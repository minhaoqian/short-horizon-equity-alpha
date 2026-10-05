import pandas as pd
import pytest
from src.data.stage1g_wrds_extraction import jobs,validate


def test_queries_are_narrow_and_distribution_payment_unfiltered():
    work=jobs()
    assert len(work)==12
    assert work[0][2].endswith('FROM crsp.stkdelists')
    distribution=[j for j in work if j[0]=='stkdistributions']
    assert len(distribution)==7
    assert all('dispaydt' not in j[2].split(' WHERE ')[1] for j in distribution)
    daily=[j for j in work if j[0]=='stkdlysecuritydata']
    assert len(daily)==4 and sum(len(j[4]) for j in daily)==7900
    assert all('dlyopen' not in j[2] for j in daily)


def test_daily_missing_requested_key_fails():
    frame=pd.DataFrame({'permno':[1],'dlycaldt':['2020-01-02'],'dlyprevdt':['2020-01-01'],'dlyretmissflg':['NA']})
    with pytest.raises(AssertionError,match='Missing'):
        validate('stkdlysecuritydata',frame,{(1,pd.Timestamp('2020-01-02').date()),(1,pd.Timestamp('2020-01-03').date())})


def test_resume_uses_validated_local_batch_without_query(tmp_path,monkeypatch):
    from src.data import stage1g_wrds_extraction as module
    monkeypatch.setattr(module,'OUT',tmp_path)
    monkeypatch.setattr(module,'COLUMNS',{'stkdelists':['permno','delistingdt']})
    monkeypatch.setattr(module,'jobs',lambda:[('stkdelists',0,'SELECT permno,delistingdt FROM crsp.stkdelists',{},None)])
    for name in ['distribution_windows.parquet','daily_missing_field_dates.parquet']:
        (tmp_path/name).write_bytes(b'fake selector fingerprint')
    class Fake:
        calls=0
        def raw_sql(self,sql,params):
            self.calls+=1
            return pd.DataFrame({'permno':[1],'delistingdt':['2020-01-02']})
    connection=Fake()
    assert module.run(connection)['complete']
    assert module.run(connection)['complete']
    assert connection.calls==1
    (tmp_path/'download_batches/stkdelists_000.parquet').write_bytes(b'changed')
    with pytest.raises(AssertionError,match='changed'):
        module.run(connection)


def test_single_login_never_invokes_retry_wrapper():
    from src.data.stage1g_wrds_extraction import single_login
    class FakeModule:
        attempts=0
        class Connection:
            def __init__(self,**kwargs):
                assert kwargs['autoconnect'] is False
            def _Connection__make_sa_engine_conn(self,raise_err):
                assert raise_err
                FakeModule.attempts+=1
                raise RuntimeError('authentication failed')
            def connect(self):
                raise AssertionError('Retry wrapper must not run')
    with pytest.raises(RuntimeError,match='authentication failed'):
        single_login(FakeModule,'example')
    assert FakeModule.attempts==1
