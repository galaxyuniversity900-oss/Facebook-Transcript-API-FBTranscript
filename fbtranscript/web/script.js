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
  const common={languages:["ar","en","all"],whisper:document.querySelector("#whisper").checked,
   language:document.querySelector("#language").value||null};
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
 document.querySelector("#warnings").textContent=(data.warnings||[]).join(" ");
 results.scrollIntoView({behavior:"smooth",block:"start"});
}
function stamp(n){const h=Math.floor(n/3600),m=Math.floor(n%3600/60),s=Math.floor(n%60);return [h,m,s].map(x=>String(x).padStart(2,"0")).join(":")}
document.querySelector("#copy").addEventListener("click",async function(){
 if(!current)return;await navigator.clipboard.writeText(current.segments.map(s=>s.text).join("\n"));
 document.querySelector("#copy").textContent="Copied";
});
document.querySelector("#format").addEventListener("change",async function(event){
 if(!current)return;
 try{
  const response=await fetch("/api/v1/export/"+event.target.value,{method:"POST",headers:{"Content-Type":"application/json"},
   body:JSON.stringify({url:currentUrl,whisper:false})});
  if(!response.ok)throw new Error("Export failed");
  const blob=await response.blob(),link=document.createElement("a");
  link.href=URL.createObjectURL(blob);link.download="fbtranscript."+event.target.value;link.click();
  URL.revokeObjectURL(link.href);
 }catch(error){alert(error.message)}
});
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
  });
  if(!data.jobs.length)list.textContent="No jobs yet.";
 }catch(error){list.textContent="History unavailable: "+error.message}
}
document.querySelector("#refresh-history").addEventListener("click",loadHistory);
loadHistory();
