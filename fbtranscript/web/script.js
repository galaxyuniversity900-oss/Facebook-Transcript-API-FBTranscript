const form=document.querySelector("#form");
const submit=document.querySelector("#submit");
const results=document.querySelector("#results");
const transcriptBox=document.querySelector("#transcript");
let current=null;
let currentUrl="";
form.addEventListener("submit",async function(event){
 event.preventDefault();
 const primary=document.querySelector("#url").value.trim();
 const batch=document.querySelector("#batch-urls").value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
 const urls=batch.length?batch:[primary];
 currentUrl=urls[0];
 submit.disabled=true;submit.textContent="Queueing…";results.hidden=true;
 try{
  const common={languages:["ar","en","all"],whisper:true,
   language:document.querySelector("#language").value||null,
   translate_to:document.querySelector("#translate-to").value||null};
  const endpoint=urls.length>1?"/api/v1/jobs/batch":"/api/v1/jobs";
  const payload=urls.length>1?Object.assign({urls:urls},common):Object.assign({url:urls[0]},common);
  const response=await fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
  const data=await response.json();
  if(!response.ok)throw new Error(data.detail||"Could not queue transcription");
  const jobs=urls.length>1?data.jobs:[data];
  submit.textContent="Transcribing…";
  const finished=await Promise.all(jobs.map(waitForJob));
  const first=finished.find(x=>x.status==="completed");
  if(first){current=first.result;render(current)}
  const failed=finished.filter(x=>x.status==="failed").length;
  if(failed)alert(failed+" job(s) failed. Review Recent jobs for details.");
  await loadHistory();
 }catch(error){alert(error.message)}
 finally{submit.disabled=false;submit.textContent="Transcribe ↗"}
});
async function waitForJob(job){
 for(let i=0;i<900;i++){
  const response=await fetch("/api/v1/jobs/"+job.id);
  const state=await response.json();
  if(state.status==="completed"||state.status==="failed"){
   if(state.status==="completed"){
    const result=await fetch("/api/v1/jobs/"+job.id+"/result");
    state.result=await result.json();
   }
   return state;
  }
  await new Promise(resolve=>setTimeout(resolve,1500));
 }
 throw new Error("Job is still running. Check Recent jobs later.");
}
function render(data){
 results.hidden=false;
 document.querySelector("#title").textContent=data.title||"Transcript";
 document.querySelector("#meta").textContent=[data.language,data.source,data.segments.length+" segments"].join(" · ");
 transcriptBox.textContent=data.segments.map(s=>"["+stamp(s.start)+"] "+s.text).join("\n\n")||"No transcript available.";
 const translated=document.querySelector("#translated");
 const translationTitle=document.querySelector("#translation-title");
 translated.hidden=!data.translated_text;
 translationTitle.hidden=!data.translated_text;
 translated.textContent=data.translated_text||"";
 document.querySelector("#warnings").textContent=(data.warnings||[]).join(" ");
 results.scrollIntoView({behavior:"smooth",block:"start"});
}
function stamp(n){const h=Math.floor(n/3600),m=Math.floor(n%3600/60),s=Math.floor(n%60);return [h,m,s].map(x=>String(x).padStart(2,"0")).join(":")}
document.querySelector("#copy").addEventListener("click",async function(){
 if(!current)return;await navigator.clipboard.writeText(current.segments.map(s=>s.text).join("\n"));
 document.querySelector("#copy").textContent="Copied";
});
document.querySelector("#format").addEventListener("change",function(event){
 if(!current)return;
 const format=event.target.value;
 let body="",type="text/plain;charset=utf-8";
 if(format==="json"){body=JSON.stringify(current,null,2);type="application/json"}
 else if(format==="txt"){body=current.segments.map(s=>s.text).join("\n");}
 else if(format==="srt"){body=current.segments.map((s,i)=>(i+1)+"\n"+subtitleStamp(s.start,true)+" --> "+subtitleStamp(s.start+s.duration,true)+"\n"+s.text).join("\n\n");type="application/x-subrip"}
 else if(format==="vtt"){body="WEBVTT\n\n"+current.segments.map(s=>subtitleStamp(s.start,false)+" --> "+subtitleStamp(s.start+s.duration,false)+"\n"+s.text).join("\n\n");type="text/vtt"}
 else{const escapeHtml=x=>String(x).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));body="<!doctype html><meta charset=\"utf-8\"><title>Transcript</title><ol>"+current.segments.map(s=>"<li>"+escapeHtml(s.text)+"</li>").join("")+"</ol>";type="text/html"}
 const blob=new Blob([body],{type:type}),link=document.createElement("a");
 link.href=URL.createObjectURL(blob);link.download="fbtranscript."+format;link.click();URL.revokeObjectURL(link.href);
});
function subtitleStamp(n,comma){const ms=Math.max(0,Math.round(n*1000)),h=Math.floor(ms/3600000),m=Math.floor(ms%3600000/60000),s=Math.floor(ms%60000/1000),x=ms%1000;return String(h).padStart(2,"0")+":"+String(m).padStart(2,"0")+":"+String(s).padStart(2,"0")+(comma?",":".")+String(x).padStart(3,"0")}

async function loadHistory(){
 const list=document.querySelector("#history-list");
 try{
  const response=await fetch("/api/v1/jobs?limit=30"),data=await response.json();
  list.replaceChildren();
  data.jobs.forEach(job=>{
   const button=document.createElement("button");
   button.type="button";button.className="history-item";
   button.textContent=job.status.toUpperCase()+" · "+(job.payload.url||"Batch video")+" · "+job.created_at;
   button.addEventListener("click",async()=>{
    const detail=await fetch("/api/v1/jobs/"+job.id).then(r=>r.json());
    if(detail.status==="completed"){
     const result=await fetch("/api/v1/jobs/"+job.id+"/result").then(r=>r.json());
     current=result;currentUrl=detail.payload.url;render(result);
    }else alert("Job status: "+detail.status+(detail.error?"\n"+detail.error:""));
   });
   list.appendChild(button);
   if(job.status==="failed"){
    const retry=document.createElement("button");retry.type="button";retry.className="history-item";
    retry.textContent="Retry job "+job.id.slice(0,8);
    retry.addEventListener("click",async()=>{
     const response=await fetch("/api/v1/jobs/"+job.id+"/retry",{method:"POST"});
     if(!response.ok){const error=await response.json();alert(error.detail||"Retry failed");return}
     await loadHistory();
    });
    list.appendChild(retry);
   }
  });
  if(!data.jobs.length)list.textContent="No jobs yet.";
 }catch(error){list.textContent="History unavailable: "+error.message}
}
document.querySelector("#refresh-history").addEventListener("click",loadHistory);
loadHistory();
