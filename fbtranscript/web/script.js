const form=document.querySelector("#form");
const submit=document.querySelector("#submit");
const results=document.querySelector("#results");
const transcriptBox=document.querySelector("#transcript");
let current=null;
let currentUrl="";
form.addEventListener("submit",async function(event){
 event.preventDefault();
 currentUrl=document.querySelector("#url").value.trim();
 submit.disabled=true;submit.textContent="Working…";results.hidden=true;
 try{
  const response=await fetch("/api/v1/transcribe",{method:"POST",headers:{"Content-Type":"application/json"},
   body:JSON.stringify({url:currentUrl,whisper:document.querySelector("#whisper").checked,
    language:document.querySelector("#language").value||null})});
  const data=await response.json();
  if(!response.ok)throw new Error(data.detail||"Transcription failed");
  current=data;render(data);
 }catch(error){alert(error.message)}
 finally{submit.disabled=false;submit.textContent="Transcribe ↗"}
});
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
