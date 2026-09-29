import os,re,requests
from flask import Flask,render_template
app=Flask(__name__)
URL=os.getenv("FRAPPE_URL","").rstrip("/")
KEY=os.getenv("FRAPPE_API_KEY",""); SECRET=os.getenv("FRAPPE_API_SECRET","")
def h():
    if not URL or not KEY or not SECRET: raise RuntimeError("Faltan variables de entorno de Frappe.")
    return {"Authorization":f"token {KEY}:{SECRET}"}
def lista():
    r=requests.get(URL+"/api/resource/HD%20Ticket",headers=h(),params={"fields":'["name","subject","status","priority","creation"]',"order_by":"creation desc","limit_page_length":100},timeout=20)
    r.raise_for_status(); return r.json().get("data",[])
def ticket(n):
    r=requests.get(URL+"/api/resource/HD%20Ticket/"+n,headers=h(),timeout=20); r.raise_for_status(); return r.json().get("data",{})
def extraer(t):
    def c(e):
        m=re.search(re.escape(e)+r"\s*:\s*(.+)",t or "",re.I); return m.group(1).strip() if m else ""
    m=re.search(r"Descripción\s*:\s*(.*)",t or "",re.I|re.S)
    return {"ciudadano":c("Ciudadano"),"telefono":c("Teléfono"),"direccion":c("Dirección"),"tipo":c("Tipo de solicitud"),"detalle":m.group(1).strip() if m else ""}
def prio(p): return {"Low":"BAJA","Medium":"MEDIA","High":"ALTA","Urgent":"ALTA"}.get(p,p or "")
@app.route("/")
def inicio():
    try:return render_template("index.html",pqrs=lista(),error=None)
    except Exception as e:return render_template("index.html",pqrs=[],error=str(e))
@app.route("/pqr/<n>")
def detalle(n):
    try:
        p=ticket(n); d=extraer(p.get("description","")); d["prioridad_ot"]=prio(p.get("priority"))
        return render_template("detalle.html",p=p,d=d,error=None)
    except Exception as e:return render_template("detalle.html",p={},d={},error=str(e)),500
@app.route("/health")
def health():return {"status":"ok"}
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
