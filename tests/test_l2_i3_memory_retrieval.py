import itertools
from sintra_live.l2.mission import MissionAggregate,MissionIdentity,MissionScope,MissionState
from sintra_live.l2.memory_contract import *
from sintra_live.l2.memory_retrieval import retrieve_memory
H="a"*64; T0="2026-08-24T10:00:00.000000Z"; NOW="2026-08-24T10:30:00.000000Z"; T1="2026-08-24T11:00:00.000000Z"
def agg():
 i=MissionIdentity("SP-LIVE-001","L2-I3","m","r",H,"p",H,"auth"); s=MissionScope("brief",("read",),("write",),"LOW",(("x",1),),0,("memory",),T1,"cancel"); b=MissionAggregate.genesis(i,s,T0); return MissionAggregate(b.schema_version,b.identity,b.scope,b.created_at,MissionState.MISSION_SCOPED,0,b.previous_event_sha256,(),(),False,False)
def query(a,required=(),count=10,bytes_=10000):
 return MemoryRetrievalQuery(QUERY_SCHEMA_VERSION,POLICY_VERSION,"SP-LIVE-001","L2-I3","tenant","p","m","r",H,H,a.version,a.aggregate_sha256, a.current_state.value,"brief",text_hash("brief"),("brief",),"status",text_hash("status"),("col",),("col",),(Classification.INTERNAL,),tuple(required),(),T0,T1,count,bytes_,"brief-writer",NOW)
def cand(id="x",content="fact",category=MemoryCategory.GOVERNED_FACT,trust=MemoryTrust.GOVERNED_FACT,kind=ContentKind.FACT,inst=(),source="m",group="",supersedes="",superseded_by="",version=1,tenant="tenant",principal="p",classification=Classification.INTERNAL,collection="col"):
 return MemoryCandidate(CANDIDATE_SCHEMA_VERSION,id,version,tenant,principal,source,collection,classification,category,trust,kind,tuple(inst),("brief",),("brief-writer",),content,text_hash(content),"src",H,T0,T0,T1,supersedes,superseded_by,group,False)
def test_hash_domains_and_formulas_reproducible():
 a=agg(); q=query(a); c=cand(); assert q.query_record_sha256==domain_hash(QUERY_DOMAIN,q.body()); assert c.candidate_record_sha256==domain_hash(CANDIDATE_DOMAIN,c.body()); assert len({QUERY_DOMAIN,CANDIDATE_DOMAIN,CANDIDATE_SET_DOMAIN,SELECTED_DOMAIN,EXCLUSION_DOMAIN,CONFLICT_DOMAIN,RECORD_DOMAIN})==7
def test_complete_and_all_bindings():
 a=agg(); r=retrieve_memory(a,query(a),(cand(),)); assert r.result is RetrievalResult.COMPLETE and r.authority_delta==0 and r.mission_id=="m" and r.aggregate_sha256==a.aggregate_sha256
def test_zero_result_semantics():
 a=agg(); assert retrieve_memory(a,query(a),()).reason_code=="NO_MATCHING_MEMORY"; r=retrieve_memory(a,query(a,(MemoryCategory.GOVERNED_FACT,)),()); assert r.result is RetrievalResult.INCOMPLETE and r.reason_code=="REQUIRED_MEMORY_MISSING"
def test_preference_and_historical_approval_flags():
 a=agg(); p=cand("p1","pref",MemoryCategory.PRINCIPAL_PREFERENCE,MemoryTrust.PRINCIPAL_PREFERENCE,ContentKind.PREFERENCE); h=cand("h1","old",MemoryCategory.HISTORICAL_APPROVAL,MemoryTrust.GOVERNED_FACT,ContentKind.HISTORICAL_APPROVAL); r=retrieve_memory(a,query(a),(p,h)); by={x.memory_item_id:x for x in r.selected_items}; assert by["p1"].presentation_only and by["h1"].prior_approval_history_only
def test_instruction_quarantined_not_selected():
 a=agg(); i=cand("i","do it",kind=ContentKind.INSTRUCTION,inst=(InstructionCategory.APPROVAL_BYPASS,)); r=retrieve_memory(a,query(a),(i,)); assert not r.selected_items and r.quarantined_items[0].reason_code=="DATA_ONLY_INSTRUCTION"
def test_input_permutations_identical():
 a=agg(); cs=(cand("a","A"),cand("b","B"),cand("c","C")); records=[retrieve_memory(a,query(a),p) for p in itertools.permutations(cs)]; assert len({r.candidate_set_sha256 for r in records})==1 and len({r.retrieval_record_sha256 for r in records})==1 and len({tuple(x.memory_item_id for x in r.selected_items) for r in records})==1
def test_classification_allowlist():
 a=agg(); r=retrieve_memory(a,query(a),(cand(classification=Classification.RESTRICTED),)); assert r.excluded_items[0].reason_code=="CLASSIFICATION_NOT_ALLOWED"
def test_cross_mission_allowlist_and_purpose():
 a=agg(); good=cand("g",source="old"); r=retrieve_memory(a,query(a),(good,)); assert r.selected_item_count==1; q=query(a); object.__setattr__(q,"cross_mission_allowed_collection_ids",()); r=retrieve_memory(a,q,(good,)); assert r.excluded_items[0].reason_code=="CROSS_MISSION_NOT_ALLOWED"
def test_count_and_byte_limits_no_truncation():
 a=agg(); r=retrieve_memory(a,query(a,count=1,bytes_=4),(cand("a","abcd"),cand("b","efgh"))); assert r.selected_item_count==1 and r.selected_items[0].content in {"abcd","efgh"} and any(x.reason_code=="RETRIEVAL_BUDGET_LIMIT" for x in r.excluded_items)
def test_valid_supersession_chain_excludes_history():
 a=agg(); old=cand("old",superseded_by="new"); new=cand("new",supersedes="old",version=2); r=retrieve_memory(a,query(a),(old,new)); assert any(x.memory_item_id=="old" and x.reason_code=="SUPERSEDED" for x in r.excluded_items) and all(x.memory_item_id!="old" for x in r.selected_items)
def test_contradiction_incomplete_no_winner():
 a=agg(); x=cand("x","yes",group="g"); y=cand("y","no",group="g"); r=retrieve_memory(a,query(a),(x,y)); assert r.result is RetrievalResult.INCOMPLETE and r.reason_code=="UNRESOLVED_CONTRADICTION" and not r.selected_items
def test_acceptance_mapping_exact(): assert {"M-01","M-02","M-03","M-04","M-05","M-06","M-07","M-08"}=={"M-%02d"%i for i in range(1,9)}
