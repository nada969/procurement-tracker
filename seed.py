"""Optional: load FICTIONAL demo data into an empty database.  python seed.py"""
from app import engine, projects, put_project, put_package, put_supplier, put_note, ProjectIn, PackageIn, SupplierIn, NoteIn
from sqlalchemy import select

with engine.begin() as c:
    if c.execute(select(projects.c.id)).first():
        raise SystemExit("Database already has data; skipping seed.")
    put_project(c, "p1", ProjectIn(name="Demo Solar PV Plant (100 MW)", client="Demo Client"))
    for k, name, budget in [("k1", "Earthing", 500000), ("k2", "Surge Arresters", 100000), ("k3", "Lighting", None)]:
        put_package(c, k, PackageIn(projectId="p1", name=name, budget=budget))
    S = [("s1","k1","Alpha Earthing Ltd","Compliant","Submitted",612000,8,"CIF port","30/70","Technically accepted"),
         ("s2","k1","Beta Grounding Co","Compliant","Submitted",548000,10,"EXW","50/50","Technically accepted"),
         ("s3","k1","Gamma Power Supplies","Non-compliant","Submitted",410000,6,"Ex-stores","100% advance","Stranded conductor offered; solid rod required"),
         ("s4","k1","Delta Metals","In review","Submitted",395000,12,"CIF port","30/70","Waiting for technical approval"),
         ("s5","k1","Epsilon Trading","Pending","Declined",None,None,"","","Vendor declined to bid"),
         ("s6","k2","Zeta Protection","Compliant","Submitted",96000,14,"CIF port","30/70","Technically accepted"),
         ("s7","k2","Eta Electrical","Clarification","Submitted",88000,16,"EXW","40/60","Datasheet missing rated discharge current")]
    for sid, k, n, tech, stage, total, lead, inco, pay, why in S:
        put_supplier(c, sid, SupplierIn(packageId=k, name=n, tech=tech, stage=stage, total=total,
                                         leadWeeks=lead, incoterm=inco, payment=pay, reason=why))
    put_note(c, "n1", NoteIn(packageId="k1", supplierId="s1", body="Called Alpha: lead time confirmed at 8 weeks, price valid 30 days.", createdAt="2026-10-12T09:30:00"))
    put_note(c, "n2", NoteIn(packageId="k1", supplierId="s3", body="Technical team rejected: stranded conductor offered, solid rod required. Asked for a compliant re-quote.", createdAt="2026-10-14T14:10:00"))
    put_note(c, "n3", NoteIn(packageId="k1", body="Bid opening done. 5 offers received, 1 declined.", createdAt="2026-10-10T11:00:00"))
print("Seeded demo data")
