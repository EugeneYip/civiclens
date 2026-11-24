// Local static-site smoke test. External requests are blocked intentionally.
const { chromium } = require("playwright-core");
const assert = require("node:assert/strict");
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||"/usr/bin/google-chrome",headless:true,args:["--no-sandbox"]});
 const ctx=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
 const page=await ctx.newPage(),errors=[],requests=[];
 page.on("pageerror",e=>{errors.push(String(e));console.error("pageerror",String(e))});
 page.on("console",m=>{if(m.type()==="error"&&!m.text().includes("Failed to load resource"))console.log("browser console",m.text())});
 page.on("request",r=>requests.push(r.url()));
 await page.route("**/*",route=>route.request().url().startsWith("http://127.0.0.1:8765/")?route.continue():route.abort());
 try{
  await page.goto("http://127.0.0.1:8765/?county=01&office=council&district=1",{waitUntil:"networkidle"});
  await page.locator(".person-row").first().waitFor();
  assert.equal(requests.filter(u=>/chief-policy-sources|policy-review-baseline|reviewed-policy-pilot|historical-review/.test(u)).length,0,"chief-only data requested on council page");
  await page.goto("http://127.0.0.1:8765/?county=05&office=chief&candidate=05-chief-4",{waitUntil:"networkidle"});
  await page.locator("#person-05-chief-4").waitFor();
  const row=page.locator("#person-05-chief-4");
  if(await row.locator(".profile-fields").count()===0)await row.locator(".person-open").click();
  await row.getByText("提出四年內詐騙案件減少80%的目標。",{exact:true}).waitFor();
  await page.locator("#person-05-chief-1 .person-toggle").click();
  await page.locator("#person-05-chief-4 .person-toggle").click();
  await page.locator('[data-view="compare"]').click();
  await page.locator('select[aria-label="政策主題"]').selectOption({label:"治理與安全"});
  await page.locator(".topic-comparison").getByText("提出四年內詐騙案件減少80%的目標。",{exact:true}).waitFor();
  await page.goto("http://127.0.0.1:8765/gazettes.html?county=17&office=chief",{waitUntil:"networkidle"});
  console.log("reader status",await page.locator("#status").textContent());
  await page.locator("#original").waitFor({timeout:10000});
  assert.ok((await page.locator("#original").getAttribute("href")).startsWith("https://bulletin.cec.gov.tw/"));
  await page.goto("http://127.0.0.1:8765/?county=06&office=chief&view=video",{waitUntil:"networkidle"});
  await page.getByText("桃園市長公辦政見發表會",{exact:true}).waitFor();
  assert.ok(await page.locator("a[href=\"https://www.youtube.com/watch?v=fEEFbC13-U0\"]").count());
  assert.equal(errors.length,0,errors.join("\n"));
  console.log("PASS: council deferred loading; chief deep link and policy summary; topic comparison; Penghu fallback; no page errors");
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
