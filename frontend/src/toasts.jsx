import React, { createContext, useContext, useState, useCallback } from 'react';
const Ctx = createContext(null);
export function ToastProvider({children}){
  const [toasts,setToasts]=useState([]);
  const push = useCallback((msg,type='info')=>{
    const id=crypto.randomUUID();
    setToasts(t=>[...t,{id,msg,type}]); setTimeout(()=>setToasts(t=>t.filter(x=>x.id!==id)),3500);
  },[]);
  return <Ctx.Provider value={{push}}>
    {children}
    <div className="fixed bottom-4 right-4 flex flex-col gap-2 z-[100]">
      {toasts.map(t=>(<div key={t.id} className={`rounded-2xl px-4 py-2 shadow-xl text-sm ${t.type==='error'?'bg-rose-600 text-white':t.type==='success'?'bg-emerald-600 text-white':'bg-black text-white'}`}>{t.msg}</div>))}
    </div>
  </Ctx.Provider>
}
export const useToast=()=>useContext(Ctx);
