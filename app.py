import os,re,requests,psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask,render_template,redirect,url_for,flash
app=Flask(__name__); app.secret_key=os.getenv("SECRET_KEY","aquasucre-prototipo")
U=os.getenv("FRAPPE_URL","").rstrip("/"); K=os.getenv("FRAPPE_API_KEY",""); S=os.getenv("FRAPPE_API_SECRET",""); D=os.getenv("DATABASE_URL","")
def h(): return {"Authorization":f"token {K}:{S}"}
def cn(): return psycopg2.connect(D,sslmode="require")
def get(path,params=None):
 r=requests.get(U+path,headers=h(),params=params,timeout=20); r.raise_for_status(); return r.json().get("data",{})
def pqrs(): return get("/api/resource/HD%20Ticket",{"fields":'["name","subject","status","priority","creation"]',"order_by":"creation desc","limit_page_length":100})
def pqr(n): return get("/api/resource/HD%20Ticket/"+n)
def parse(t):
 def c(x):
  m=re.search(re.escape(x)+r"\s*:\s*(.+)",t or "",re.I); return m.group(1).strip() if m else ""
 m=re.search(r"Descripción\s*:\s*(.*)",t or "",re.I|re.S)
 return {"ciudadano":c("Ciudadano"),"telefono":c("Teléfono"),"direccion":c("Dirección"),"tipo":c("Tipo de solicitud"),"descripcion":m.group(1).strip() if m else ""}
def pri(p): return {"Low":"BAJA","Medium":"MEDIA","High":"ALTA","Urgent":"URGENTE"}.get(p,"MEDIA")
def ot(n):
 with cn() as c:
  with c.cursor(cursor_factory=RealDictCursor) as q:
   q.execute("SELECT id_ot,id_pqr,id_tecnico,estado,prioridad FROM ordenes_trabajo WHERE id_pqr=%s",(n,)); return q.fetchone()
@app.route("/")
def home():
 try:return render_template("index.html",pqrs=pqrs(),error=None)
 except Exception as e:return render_template("index.html",pqrs=[],error=str(e))
@app.route("/pqr/<n>")
def detail(n):
 try:
  p=pqr(n); d=parse(p.get("description","")); d["prioridad"]=pri(p.get("priority"))
  return render_template("detail.html",p=p,d=d,ot=ot(n),error=None)
 except Exception as e:return render_template("detail.html",p={},d={},ot=None,error=str(e)),500
@app.post("/pqr/<n>/generar")
def generar(n):
 try:
  x=ot(n)
  if x: flash(f"La PQR {n} ya tiene la OT {x['id_ot']}.","info"); return redirect(url_for("detail",n=n))
  p=pqr(n); d=parse(p.get("description",""))
  if not d["tipo"] or not d["direccion"] or not d["descripcion"]:
   flash("No se puede generar la OT: faltan tipo de servicio, dirección o descripción.","error"); return redirect(url_for("detail",n=n))
  with cn() as c:
   with c.cursor() as q:
    q.execute("""INSERT INTO ordenes_trabajo(id_pqr,tipo_servicio,descripcion,direccion,prioridad,id_tecnico,estado)
    VALUES(%s,%s,%s,%s,%s,NULL,'PENDIENTE') RETURNING id_ot""",(n,d["tipo"],d["descripcion"],d["direccion"],pri(p.get("priority"))))
    i=q.fetchone()[0]
   c.commit()
  flash(f"Orden de Trabajo {i} creada correctamente para la PQR {n}.","success")
 except Exception as e: flash("No fue posible generar la OT: "+str(e),"error")
 return redirect(url_for("detail",n=n))
@app.post("/sincronizar")
def sync():
 ok=ya=0; errs=[]
 try:
  with cn() as c:
   with c.cursor(cursor_factory=RealDictCursor) as q:
    q.execute("SELECT id_ot,id_pqr FROM ordenes_trabajo WHERE estado='FINALIZADA' AND id_pqr IS NOT NULL ORDER BY id_ot"); rows=q.fetchall()
  for x in rows:
   try:
    p=pqr(x["id_pqr"])
    if p.get("status")=="Resolved": ya+=1; continue
    r=requests.put(U+"/api/resource/HD%20Ticket/"+x["id_pqr"],headers={**h(),"Content-Type":"application/json"},json={"status":"Resolved"},timeout=20); r.raise_for_status(); ok+=1
   except Exception as e: errs.append(f"OT {x['id_ot']}/PQR {x['id_pqr']}: {e}")
  if ok: flash(f"{ok} PQR actualizada(s) a Resolved.","success")
  if ya: flash(f"{ya} PQR ya estaba(n) en Resolved.","info")
  if not rows: flash("No hay OT FINALIZADAS para sincronizar.","info")
  if errs: flash("Errores: "+" | ".join(errs),"error")
 except Exception as e: flash("No fue posible consultar Neon: "+str(e),"error")
 return redirect(url_for("home"))
@app.route("/health")
def health(): return {"status":"ok"}
