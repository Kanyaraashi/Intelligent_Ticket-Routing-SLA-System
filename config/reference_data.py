"""Static reference data seeded into the database. All business configuration lives here or in the DB."""
PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
LANGUAGES = [("en","English",0.50),("es","Spanish",0.15),("hi","Hindi",0.12),("fr","French",0.08),("de","German",0.08),("pt","Portuguese",0.07)]
# channel_id, name, work_days (Mon=0), open_min_utc, close_min_utc, arrival weight
CHANNELS = [("EMAIL","Email","0,1,2,3,4",480,1080,0.45),("CHAT","Live chat","0,1,2,3,4,5",360,1320,0.35),("PHONE","Phone","0,1,2,3,4",420,1140,0.20)]
SKILLS = [("BILLING","Billing"),("TECHNICAL","Technical support"),("ACCOUNT","Account access"),("LOGISTICS","Logistics"),
          ("RETENTION","Retention"),("SAFETY","Product safety"),("GENERAL","General enquiries")]
QUEUES = [("Q-BILLING","Billing Queue","BILLING"),("Q-TECH","Technical Queue","TECHNICAL"),("Q-ACCOUNT","Account Queue","ACCOUNT"),
          ("Q-LOGISTICS","Logistics Queue","LOGISTICS"),("Q-RETENTION","Retention Queue","RETENTION"),
          ("Q-SAFETY","Safety Incident Queue","SAFETY"),("Q-GENERAL","General Queue","GENERAL")]
SAFETY_KEYWORDS = ["overheating","smoke","caught fire","sparks","burn","electric shock","melted","exploded"]
# intent_id: name, skills, default priority, queue, weight, keywords, (subject, body) templates
INTENTS = {
 "BILLING_DISPUTE": dict(name="Billing dispute", skills=["BILLING"], priority="MEDIUM", queue="Q-BILLING", weight=10,
   keywords=["charged twice","double charged","incorrect charge","billing error","overcharged"],
   templates=[("Wrong charge on invoice {ref}","I was charged twice on invoice {ref}. Please reverse the incorrect charge."),
              ("Billing error","There is a billing error on my statement {ref}, I was overcharged.")]),
 "PAYMENT_FAILED": dict(name="Payment failed", skills=["BILLING"], priority="MEDIUM", queue="Q-BILLING", weight=8,
   keywords=["payment failed","card declined","payment was declined","transaction failed"],
   templates=[("Payment failed","My payment failed for order {ref} and the card declined with no reason."),
              ("Transaction failed","The transaction failed at checkout, my payment was declined.")]),
 "PASSWORD_RESET": dict(name="Password reset", skills=["ACCOUNT"], priority="LOW", queue="Q-ACCOUNT", weight=14,
   keywords=["reset my password","forgot password","password reset","reset link"],
   templates=[("Need to reset my password","I forgot password for my account and the reset link never arrives."),
              ("Password reset help","Please help me reset my password, ref {ref}.")]),
 "LOGIN_ISSUE": dict(name="Login issue", skills=["ACCOUNT"], priority="MEDIUM", queue="Q-ACCOUNT", weight=10,
   keywords=["cannot log in","can't log in","locked out","login error","two-factor"],
   templates=[("Cannot log in","I cannot log in to my account, it shows a login error since yesterday."),
              ("Locked out","I am locked out after the two-factor code stopped arriving.")]),
 "TECH_FAULT": dict(name="Technical fault", skills=["TECHNICAL"], priority="MEDIUM", queue="Q-TECH", weight=15,
   keywords=["stopped working","error code","crashes","firmware","won't turn on","device fault"],
   templates=[("Device stopped working","My device stopped working after the last firmware update, error code E{ref}."),
              ("App crashes","The app crashes every time I open it, ticket ref {ref}."),
              ("Won't turn on","The unit won't turn on at all since this morning.")]),
 "DELIVERY_STATUS": dict(name="Delivery status", skills=["LOGISTICS"], priority="LOW", queue="Q-LOGISTICS", weight=16,
   keywords=["where is my order","delivery delayed","tracking","not delivered","package"],
   templates=[("Where is my order {ref}","Where is my order {ref}? The tracking has not updated for days."),
              ("Package not delivered","My package was marked as not delivered, delivery delayed again.")]),
 "REFUND_REQUEST": dict(name="Refund request", skills=["BILLING"], priority="MEDIUM", queue="Q-BILLING", weight=9,
   keywords=["refund","money back","return my order"],
   templates=[("Refund request {ref}","I would like a refund for order {ref}, I want my money back."),
              ("Return my order","Please let me return my order {ref} and process the refund.")]),
 "CANCELLATION": dict(name="Cancellation", skills=["RETENTION"], priority="MEDIUM", queue="Q-RETENTION", weight=6,
   keywords=["cancel my subscription","cancel my account","close my account","cancellation"],
   templates=[("Cancel my subscription","I want to cancel my subscription effective this month, ref {ref}."),
              ("Close my account","Please close my account, this is a cancellation request.")]),
 "PRODUCT_SAFETY": dict(name="Product safety incident", skills=["SAFETY","TECHNICAL"], priority="CRITICAL", queue="Q-SAFETY", weight=2.5, safety=True,
   keywords=SAFETY_KEYWORDS,
   templates=[("Charger overheating","My charger is overheating and there was smoke from the plug. Order {ref}."),
              ("Battery melted","The battery melted and I saw sparks, I am worried. Ref {ref}."),
              ("Device caught fire","The device caught fire while charging overnight. Ref {ref}.")]),
 "GENERAL_QUERY": dict(name="General query", skills=["GENERAL"], priority="LOW", queue="Q-GENERAL", weight=9.5,
   keywords=["question","information","how do i","opening hours","feedback"],
   templates=[("Question about service","I have a question about your service and need some information."),
              ("Feedback","I would like to leave some feedback, how do I contact the team? Ref {ref}.")]),
}
VAGUE_TEMPLATES = [("Need help","Hello, I need some help with my situation, thanks."), ("Hi","Can someone get back to me please?")]
PRIORITY_RULES = [("PR-%02d"%i,"KEYWORD",k,"CRITICAL",1) for i,k in enumerate(SAFETY_KEYWORDS,1)] + [
  ("PR-20","KEYWORD","urgent","HIGH",0),("PR-21","KEYWORD","asap","HIGH",0),("PR-22","KEYWORD","immediately","HIGH",0),
  ("PR-23","KEYWORD","outage","HIGH",0),("PR-24","KEYWORD","lawyer","HIGH",0),("PR-30","TIER_BUMP","PLATINUM","HIGH",0)]
# SLA targets in WORKING minutes: priority -> (response by channel, resolution)
_RESP = {"CRITICAL":(15,5,5),"HIGH":(60,10,10),"MEDIUM":(240,20,20),"LOW":(480,60,60)}
_RESOL = {"CRITICAL":240,"HIGH":480,"MEDIUM":1200,"LOW":2400}
SLA_POLICY = [(f"POL-{p}-{c}",p,c,_RESP[p][i],_RESOL[p],1 if p=="CRITICAL" else 0)
              for p in PRIORITIES for i,c in enumerate(["EMAIL","CHAT","PHONE"])]
HOLIDAYS = [("HOL-01","2026-07-03",None,"Independence Day (observed)"),("HOL-02","2026-08-15","PHONE","Phone-center closure"),
            ("HOL-03","2026-09-07",None,"Labour Day")]
ESCALATION_FRACTION = 0.5   # escalate unassigned tickets after 50% of response target (working minutes)
TRANSITIONS = {
 "NEW":["OPEN"], "OPEN":["ASSIGNED","ESCALATED"], "ASSIGNED":["IN_PROGRESS","OPEN","ESCALATED"],
 "IN_PROGRESS":["PENDING_CUSTOMER","RESOLVED","ESCALATED","OPEN","ASSIGNED"],
 "PENDING_CUSTOMER":["IN_PROGRESS","RESOLVED"], "RESOLVED":["CLOSED","REOPENED"],
 "CLOSED":["REOPENED"], "REOPENED":["ASSIGNED","ESCALATED"], "ESCALATED":["ASSIGNED","IN_PROGRESS"]}
