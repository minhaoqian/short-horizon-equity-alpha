from datetime import date
import pytest
from src.features.events import EventLayer
from src.data.stage2a_event_extraction import SQL,BATCHES,COLUMNS

D=date(2005,1,28);P=date(2005,1,27)


def event(**changes):
    row=dict(permno=1,disexdt=D,disdeclaredt=P,dispaymenttype='USD',distype='CD',
        disdetailtype='CDIV',disdivamt=1.0,disfacpr=0.0,disfacshr=0.0,dispermno=0)
    return {**row,**changes}


def test_complete_global_query_preserves_zero_rights_and_no_outcome_selection():
    predicate=SQL.split('WHERE')[1]
    assert predicate==' disexdt >= %(lo)s AND disexdt < %(hi)s'
    assert 'disdeclaredt' in COLUMNS
    assert all(left[1]==right[0] for left,right in zip(BATCHES,BATCHES[1:]))


@pytest.mark.parametrize('detail,payment',[('SECRD','OP'),('URTSD','X')])
def test_zero_impact_rights_not_event_free(detail,payment):
    layer=EventLayer([event(disdetailtype=detail,dispaymenttype=payment,distype='SP',
        disdivamt=0.0,disdeclaredt=None)],[])
    result=layer.interval(1,P,D,D)
    assert result.distribution_count==1
    assert result.gap_admissible is False and result.return_admissible is False


def test_after_asof_events_do_not_influence_admissibility_and_outcomes_ignored():
    future=date(2005,2,1)
    layer=EventLayer([event(disexdt=future,disdeclaredt=future,target_status='unresolved')],[])
    assert layer.interval(1,P,D,D)==EventLayer([],[]).interval(1,P,D,D)
    with pytest.raises(ValueError):
        layer.interval(1,P,future,D)


def test_cash_and_splits_exclude_gap_and_ignore_future_payment():
    row=event(dispaydt=date(2030,1,1))
    result=EventLayer([row],[]).interval(1,P,D,D)
    assert result.return_admissible is True and result.gap_admissible is False
    split=event(dispaymenttype='SS',distype='FRS',disdetailtype='STKSPL',disfacshr=1,disfacpr=1)
    assert EventLayer([split],[]).interval(1,P,D,D).event_type=='pure_split'
    assert EventLayer([row,split],[]).interval(1,P,D,D).event_type=='ordinary_cash_and_split'


def test_future_declaration_requires_review_not_silent_missing_label_rule():
    row=event(disdeclaredt=date(2005,2,3))
    result=EventLayer([row],[]).interval(1,P,D,D)
    assert result.return_admissible is None and result.gap_admissible is None
    assert result.reason=='declaration_after_effective_ex_date'
    assert EventLayer([event(disdeclaredt=None)],[]).interval(1,P,D,D).return_admissible is None


def test_delisting_last_price_and_later_amount_do_not_mask_earlier_interval():
    r=dict(permno=1,delistingdt=D,deldlydt=date(2005,1,31),delamtdt=date(2005,6,1),delret=-1)
    layer=EventLayer([],[r])
    assert layer.interval(1,P,D,D).return_admissible is True
    assert layer.interval(1,D,date(2005,1,31),date(2005,1,31)).return_admissible is False
    assert EventLayer([],[{**r,'delamtdt':date(2030,1,1),'delret':10}]).interval(1,P,D,D)==layer.interval(1,P,D,D)


def test_absence_verified_for_unselected_security_and_coverage_explicit():
    assert EventLayer([event()],[]).interval(999999,P,D,D).gap_admissible is True
    assert EventLayer([],[]).interval(1,date(1990,1,1),D,D).return_admissible is None
