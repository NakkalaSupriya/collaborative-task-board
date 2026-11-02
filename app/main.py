from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
import json, uuid, asyncio
from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .database import connect, init_db
from .seed import seed

STATIC = Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(app):
    init_db()
    seed()
    yield

app = FastAPI(title="Collaborative Task Board API", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
class Hub:
    def __init__(self):
        self.connections = {}  # tenant_id -> [(websocket, user_id)]
        self.lock = asyncio.Lock()
    async def add(self, tenant, ws, user):
        async with self.lock: self.connections.setdefault(tenant, []).append((ws,user))
    async def remove(self, tenant, ws):
        async with self.lock:
            self.connections[tenant] = [(w,u) for w,u in self.connections.get(tenant,[]) if w != ws]
            if not self.connections[tenant]: self.connections.pop(tenant, None)
    async def broadcast(self, tenant, message):
        async with self.lock: peers = list(self.connections.get(tenant, []))
        stale=[]
        for ws,_ in peers:
            try: await ws.send_json(message)
            except Exception: stale.append(ws)
        for ws in stale: await self.remove(tenant,ws)
    def presence(self, tenant):
        return list(dict.fromkeys(u for _,u in self.connections.get(tenant,[])))
hub=Hub()

def rowdict(row): return dict(row) if row else None
def get_user(user_id):
    with connect() as c:
        u=c.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
    if not u: raise HTTPException(401,"Unknown demo user. Select a seeded user.")
    return rowdict(u)
def access(user_id, tenant_id, write=False):
    get_user(user_id)
    with connect() as c:
        t=c.execute("SELECT * FROM tenants WHERE id=?",(tenant_id,)).fetchone()
        if not t: raise HTTPException(404,"Tenant not found")
        memberships=c.execute("SELECT * FROM memberships WHERE user_id=? AND organization_id=?",(user_id,t["organization_id"])).fetchall()
    allowed=any(m["role"]=="org_admin" or (m["tenant_id"]==tenant_id) for m in memberships)
    if not allowed: raise HTTPException(404,"Tenant not found")
    roles=[m["role"] for m in memberships if m["role"]=="org_admin" or m["tenant_id"]==tenant_id]
    if write and not any(r in ("org_admin","tenant_admin","member") for r in roles):
        raise HTTPException(403,"Insufficient permissions")
    return t, roles
def can_manage(user_id, tenant_id):
    _,roles=access(user_id,tenant_id)
    if not any(r in ("org_admin","tenant_admin") for r in roles):
        raise HTTPException(403,"Admin role required")

class OrgIn(BaseModel): name: str = Field(min_length=1,max_length=100)
class TenantIn(BaseModel): organization_id: str; name: str = Field(min_length=1,max_length=100)
class BoardIn(BaseModel): name: str = Field(min_length=1,max_length=120)
class ColumnIn(BaseModel): name: str = Field(min_length=1,max_length=80); position: int = 0
class TaskIn(BaseModel):
    title: str = Field(min_length=1,max_length=200)
    description: str = ""
    column_id: str
    position: int = 0
    expected_version: Optional[int] = None

@app.get("/")
def home(): return FileResponse(STATIC / "index.html")

@app.get("/api/users")
def users():
    with connect() as c: return [rowdict(r) for r in c.execute("SELECT id,name FROM users ORDER BY name")]

@app.get("/api/organizations")
def organizations(x_user_id: str = Header(default="u-member")):
    get_user(x_user_id)
    with connect() as c:
        rows=c.execute("""SELECT DISTINCT o.* FROM organizations o JOIN memberships m
        ON m.organization_id=o.id WHERE m.user_id=? OR EXISTS
        (SELECT 1 FROM memberships x WHERE x.user_id=? AND x.role='org_admin' AND x.organization_id=o.id)
        ORDER BY o.name""",(x_user_id,x_user_id)).fetchall()
    return [rowdict(r) for r in rows]

@app.post("/api/organizations")
async def create_org(data: OrgIn, x_user_id: str=Header(default="u-org-admin")):
    get_user(x_user_id)
    oid="org-"+uuid.uuid4().hex[:10]
    with connect() as c:
        c.execute("INSERT INTO organizations(id,name) VALUES (?,?)",(oid,data.name))
        c.execute("INSERT INTO memberships(user_id,organization_id,role) VALUES (?,?,?)",(x_user_id,oid,"org_admin"))
    return {"id":oid,"name":data.name}

@app.get("/api/tenants")
def tenants(organization_id: str, x_user_id: str=Header(default="u-member")):
    get_user(x_user_id)
    with connect() as c:
        org=c.execute("SELECT * FROM organizations WHERE id=?",(organization_id,)).fetchone()
        if not org: raise HTTPException(404,"Organization not found")
        rows=c.execute("""SELECT DISTINCT t.* FROM tenants t LEFT JOIN memberships m ON m.tenant_id=t.id
        WHERE t.organization_id=? AND (m.user_id=? OR EXISTS
        (SELECT 1 FROM memberships x WHERE x.user_id=? AND x.organization_id=t.organization_id AND x.role='org_admin'))
        ORDER BY t.name""",(organization_id,x_user_id,x_user_id)).fetchall()
    return [rowdict(r) for r in rows]

@app.post("/api/tenants")
def create_tenant(data: TenantIn, x_user_id: str=Header(default="u-org-admin")):
    with connect() as c:
        m=c.execute("SELECT role FROM memberships WHERE user_id=? AND organization_id=?",(x_user_id,data.organization_id)).fetchall()
        if not any(r["role"]=="org_admin" for r in m): raise HTTPException(403,"Organization admin required")
        tid="tenant-"+uuid.uuid4().hex[:10]
        c.execute("INSERT INTO tenants(id,organization_id,name) VALUES (?,?,?)",(tid,data.organization_id,data.name))
        c.execute("INSERT INTO memberships(user_id,organization_id,tenant_id,role) VALUES (?,?,?,?)",(x_user_id,data.organization_id,tid,"tenant_admin"))
        bid="board-"+uuid.uuid4().hex[:10]
        c.execute("INSERT INTO boards(id,tenant_id,name) VALUES (?,?,?)",(bid,tid,"Main Board"))
        for i,n in enumerate(["To Do","In Progress","Done"]):
            c.execute("INSERT INTO columns(id,tenant_id,board_id,name,position) VALUES (?,?,?,?,?)",(f"{tid}-col-{i}",tid,bid,n,i))
    return {"id":tid,"organization_id":data.organization_id,"name":data.name}

@app.get("/api/board")
def get_board(tenant_id: str, x_user_id: str=Header(default="u-member")):
    access(x_user_id,tenant_id)
    with connect() as c:
        b=c.execute("SELECT * FROM boards WHERE tenant_id=? ORDER BY created_at LIMIT 1",(tenant_id,)).fetchone()
        if not b: return {"board":None,"columns":[]}
        cols=c.execute("SELECT * FROM columns WHERE tenant_id=? AND board_id=? ORDER BY position",(tenant_id,b["id"])).fetchall()
        result=[]
        for col in cols:
            tasks=c.execute("SELECT * FROM tasks WHERE tenant_id=? AND column_id=? ORDER BY position,updated_at",(tenant_id,col["id"])).fetchall()
            result.append({"column":rowdict(col),"tasks":[rowdict(t) for t in tasks]})
    return {"board":rowdict(b),"columns":result}

@app.post("/api/boards")
def create_board(tenant_id: str, data: BoardIn, x_user_id: str=Header(default="u-org-admin")):
    can_manage(x_user_id,tenant_id)
    bid="board-"+uuid.uuid4().hex[:10]
    with connect() as c: c.execute("INSERT INTO boards(id,tenant_id,name) VALUES (?,?,?)",(bid,tenant_id,data.name))
    return {"id":bid,"tenant_id":tenant_id,"name":data.name}

@app.post("/api/columns")
def create_column(tenant_id: str, board_id: str, data: ColumnIn, x_user_id: str=Header(default="u-org-admin")):
    can_manage(x_user_id,tenant_id)
    with connect() as c:
        b=c.execute("SELECT id FROM boards WHERE id=? AND tenant_id=?",(board_id,tenant_id)).fetchone()
        if not b: raise HTTPException(404,"Board not found")
        cid="col-"+uuid.uuid4().hex[:10]
        c.execute("INSERT INTO columns(id,tenant_id,board_id,name,position) VALUES (?,?,?,?,?)",(cid,tenant_id,board_id,data.name,data.position))
    return {"id":cid,"tenant_id":tenant_id,"board_id":board_id,"name":data.name,"position":data.position}

@app.post("/api/tasks")
async def create_task(tenant_id: str, data: TaskIn, x_user_id: str=Header(default="u-member")):
    access(x_user_id,tenant_id,write=True)
    tid="task-"+uuid.uuid4().hex[:10]
    with connect() as c:
        col=c.execute("SELECT * FROM columns WHERE id=? AND tenant_id=?",(data.column_id,tenant_id)).fetchone()
        if not col: raise HTTPException(404,"Column not found")
        board=c.execute("SELECT * FROM boards WHERE id=? AND tenant_id=?",(col["board_id"],tenant_id)).fetchone()
        c.execute("""INSERT INTO tasks(id,tenant_id,board_id,column_id,title,description,position)
        VALUES (?,?,?,?,?,?,?)""",(tid,tenant_id,board["id"],data.column_id,data.title,data.description,data.position))
        c.execute("INSERT INTO activity_logs(tenant_id,user_id,task_id,action,details) VALUES (?,?,?,?,?)",(tenant_id,x_user_id,tid,"created",data.title))
        task=rowdict(c.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone())
    await hub.broadcast(tenant_id,{"type":"task_created","task":task})
    return task

@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, tenant_id: str, data: TaskIn, x_user_id: str=Header(default="u-member")):
    access(x_user_id,tenant_id,write=True)
    with connect() as c:
        old=c.execute("SELECT * FROM tasks WHERE id=? AND tenant_id=?",(task_id,tenant_id)).fetchone()
        if not old: raise HTTPException(404,"Task not found")
        if data.expected_version is not None and data.expected_version != old["version"]:
            raise HTTPException(409,detail={"message":"Version conflict","current":rowdict(old)})
        col=c.execute("SELECT * FROM columns WHERE id=? AND tenant_id=?",(data.column_id,tenant_id)).fetchone()
        if not col: raise HTTPException(404,"Column not found")
        action="moved" if old["column_id"]!=data.column_id or old["position"]!=data.position else "updated"
        c.execute("""UPDATE tasks SET title=?,description=?,column_id=?,position=?,version=version+1,
        updated_at=CURRENT_TIMESTAMP WHERE id=? AND tenant_id=?""",
        (data.title,data.description,data.column_id,data.position,task_id,tenant_id))
        c.execute("INSERT INTO activity_logs(tenant_id,user_id,task_id,action,details) VALUES (?,?,?,?,?)",(tenant_id,x_user_id,task_id,action,data.title))
        task=rowdict(c.execute("SELECT * FROM tasks WHERE id=? AND tenant_id=?",(task_id,tenant_id)).fetchone())
    await hub.broadcast(tenant_id,{"type":"task_updated","task":task})
    return task

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, tenant_id: str, x_user_id: str=Header(default="u-member")):
    access(x_user_id,tenant_id,write=True)
    with connect() as c:
        task=c.execute("SELECT * FROM tasks WHERE id=? AND tenant_id=?",(task_id,tenant_id)).fetchone()
        if not task: raise HTTPException(404,"Task not found")
        c.execute("DELETE FROM tasks WHERE id=? AND tenant_id=?",(task_id,tenant_id))
        c.execute("INSERT INTO activity_logs(tenant_id,user_id,task_id,action,details) VALUES (?,?,?,?,?)",(tenant_id,x_user_id,task_id,"deleted",task["title"]))
    await hub.broadcast(tenant_id,{"type":"task_deleted","task_id":task_id})
    return {"ok":True}

@app.get("/api/activity")
def activity(tenant_id: str, x_user_id: str=Header(default="u-member")):
    access(x_user_id,tenant_id)
    with connect() as c:
        return [rowdict(r) for r in c.execute("""SELECT a.*,u.name AS user_name FROM activity_logs a
        JOIN users u ON u.id=a.user_id WHERE a.tenant_id=? ORDER BY a.id DESC LIMIT 50""",(tenant_id,))]

@app.websocket("/ws/{tenant_id}")
async def websocket_endpoint(ws: WebSocket, tenant_id: str, user_id: str="u-member"):
    try:
        access(user_id,tenant_id)
    except HTTPException:
        await ws.close(code=1008)
        return
    await ws.accept()
    await hub.add(tenant_id,ws,user_id)
    await hub.broadcast(tenant_id,{"type":"presence","users":hub.presence(tenant_id)})
    try:
        while True:
            await ws.receive_text()  # client heartbeat
    except WebSocketDisconnect:
        await hub.remove(tenant_id,ws)
        await hub.broadcast(tenant_id,{"type":"presence","users":hub.presence(tenant_id)})
