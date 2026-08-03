// Execute the built page's inline JS against a minimal DOM shim. Catches
// load-time errors (TDZ, typos, bad meta access) that node --check cannot.
import { readFileSync } from 'node:fs';

// Usage: node scripts/smoke-page.mjs [built-page.html]
const target = process.argv[2] || 'pr-control.html';
const html = readFileSync(target, 'utf8');
const js = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');

const mk = () => new Proxy({
  innerHTML: '', textContent: '', value: '', style: {}, dataset: {}, classList: {
    add(){}, remove(){}, toggle(){}, contains(){ return false; } },
  children: [], appendChild(){}, removeChild(){}, setAttribute(){}, getAttribute(){ return null; },
  addEventListener(){}, removeEventListener(){}, querySelector(){ return mk(); },
  querySelectorAll(){ return []; }, closest(){ return null; }, focus(){}, scrollIntoView(){},
  getBoundingClientRect(){ return {top:0,left:0,width:100,height:100,bottom:0,right:0}; },
}, { get(t, k){ return k in t ? t[k] : (typeof k === 'string' ? mk() : undefined); }, set(t,k,v){ t[k]=v; return true; } });

globalThis.document = {
  documentElement: mk(), body: mk(), head: mk(), title: '',
  getElementById: () => mk(), querySelector: () => mk(), querySelectorAll: () => [],
  createElement: () => mk(), addEventListener(){}, createTextNode: () => mk(),
};
globalThis.window = { addEventListener(){}, matchMedia: () => ({ matches:false, addEventListener(){} }),
  location:{hash:'',href:''}, localStorage:{getItem:()=>null,setItem(){}}, requestAnimationFrame:(f)=>f(0),
  getComputedStyle: () => ({ getPropertyValue: () => '' }), innerWidth: 1200, innerHeight: 800 };
Object.defineProperty(globalThis, 'navigator', { value: { clipboard: { writeText: async () => {} } }, configurable: true });
globalThis.localStorage = window.localStorage;
globalThis.requestAnimationFrame = window.requestAnimationFrame;
globalThis.getComputedStyle = window.getComputedStyle;
globalThis.addEventListener = () => {};
globalThis.removeEventListener = () => {};
globalThis.setTimeout = globalThis.setTimeout || (() => 0);
globalThis.matchMedia = window.matchMedia;
globalThis.innerWidth = 1200;
globalThis.location = window.location;

try { new Function(js)(); console.log(`✔ ${target} executed with no load-time error`); }
catch (e) { console.error(`✖ ${target} threw at load:`, e.constructor.name + ':', e.message); process.exit(1); }
