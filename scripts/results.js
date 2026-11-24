"use strict";
const opening=Date.parse("2026-11-28T16:00:00+08:00");
function resultPhase(now){return now<opening?"投票截止後開放官方開票查詢｜11/28 16:00（臺灣時間）":"已達預定開票時間；請查閱中選會實際發布狀態。"}
function update(){document.getElementById("phase").textContent=resultPhase(Date.now())}
update();setInterval(update,30000);document.addEventListener("visibilitychange",()=>{if(!document.hidden)update()});