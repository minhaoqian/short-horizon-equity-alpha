from src.features.historical_source_qa import looks_event_free


def test_daily_zero_effect_screen_is_not_event_free_evidence():
    # Same source fields, different corporate-action histories: the daily screen
    # alone cannot supply the fixture's required verified-none evidence.
    clean=dict(dlyfacprc=1,dlyorddivamt=0,dlynonorddivamt=0,dlydelflg='N')
    rights={**clean,'disdetailtype':'SECRD','dispaymenttype':'OP'}
    unknown={**clean,'disdetailtype':'URTSD','dispaymenttype':'X'}
    assert looks_event_free(clean) and looks_event_free(rights) and looks_event_free(unknown)
    from src.features.returns import event_free
    from datetime import date
    d=date(2005,1,28)
    assert not event_free({**rights,'event_verified':False},d)
    assert not event_free({**unknown,'event_verified':False},d)
