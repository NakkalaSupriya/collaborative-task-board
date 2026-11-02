from .database import connect

def seed():
    with connect() as c:
        if c.execute("SELECT COUNT(*) FROM organizations").fetchone()[0]:
            return
        c.executemany("INSERT INTO organizations(id,name) VALUES (?,?)", [
            ("org-acme","Acme Technologies"), ("org-northstar","Northstar Labs")])
        c.executemany("INSERT INTO tenants(id,organization_id,name) VALUES (?,?,?)", [
            ("tenant-hyd","org-acme","Hyderabad"), ("tenant-blr","org-acme","Bengaluru"),
            ("tenant-chen","org-acme","Chennai"), ("tenant-north","org-northstar","Pune")])
        c.executemany("INSERT INTO users(id,name,email) VALUES (?,?,?)", [
            ("u-org-admin","Olivia Org Admin","olivia@example.com"),
            ("u-tenant-admin","Tara Tenant Admin","tara@example.com"),
            ("u-member","Milan Member","milan@example.com")])
        c.executemany("INSERT INTO memberships(user_id,organization_id,tenant_id,role) VALUES (?,?,?,?)", [
            ("u-org-admin","org-acme",None,"org_admin"),
            ("u-tenant-admin","org-acme","tenant-hyd","tenant_admin"),
            ("u-member","org-acme","tenant-hyd","member"),
            ("u-member","org-acme","tenant-blr","member")])
        c.execute("INSERT INTO boards(id,tenant_id,name) VALUES (?,?,?)",
                  ("board-hyd","tenant-hyd","Product Delivery"))
        c.executemany("INSERT INTO columns(id,tenant_id,board_id,name,position) VALUES (?,?,?,?,?)", [
            ("col-todo","tenant-hyd","board-hyd","To Do",0),
            ("col-doing","tenant-hyd","board-hyd","In Progress",1),
            ("col-done","tenant-hyd","board-hyd","Done",2)])
        c.executemany("""INSERT INTO tasks(id,tenant_id,board_id,column_id,title,description,position)
                         VALUES (?,?,?,?,?,?,?)""", [
            ("task-1","tenant-hyd","board-hyd","col-todo","Design task board","Create the initial Kanban layout.",0),
            ("task-2","tenant-hyd","board-hyd","col-doing","Build tenant API","Enforce tenant scope on every route.",0),
            ("task-3","tenant-hyd","board-hyd","col-done","Agree on schema","Organizations, tenants, memberships and tasks.",0)])
