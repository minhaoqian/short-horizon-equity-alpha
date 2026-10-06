from src.features.timing_qa import reconcile


def test_ordinary_cash_flag_not_payment_frequency_controls_daily_bucket():
    events=[dict(dispaymenttype='USD',distype='SD',disordinaryflg='Y',disdivamt=1.,dispermno=0,disfacpr=0.)]
    daily=dict(dlyorddivamt=1.,dlynonorddivamt=0.,dlyfacprc=1.,dlyprc=10.,dlyprevprc=10.,dlyret=.1)
    assert reconcile(events,daily)[0]
    assert not reconcile(events,{**daily,'dlyorddivamt':2.})[0]
    assert not reconcile(events,None)[0]


def test_metadata_and_outcomes_do_not_repair_missing_daily_evidence():
    event=dict(dispaymenttype='USD',distype='CD',disordinaryflg='Y',disdivamt=1.,dispermno=0,disfacpr=0.,disdeclaredt='future',dispaydt='future',target_status='observed')
    assert not reconcile([event],None)[0]
    assert not reconcile([{**event,'dispaymenttype':'OS'}],{})[0]
