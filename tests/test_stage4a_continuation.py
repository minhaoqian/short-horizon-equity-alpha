import pandas as pd
import numpy as np
import pytest
from src.portfolio.continuation import halt_mask


def test_halt_applies_at_known_close_not_previous_submission():
    cal=pd.to_datetime(['2003-01-10','2003-01-13','2003-01-14'])
    np.testing.assert_array_equal(halt_mask(cal,{'order':'2003-01-13'}),[True,False,False])


def test_only_verified_termination_releases_halt():
    cal=pd.date_range('2003-01-10',periods=6)
    np.testing.assert_array_equal(halt_mask(cal,{'a':'2003-01-11'},{'a':'2003-01-14'}),[True,False,False,False,True,True])
    assert not halt_mask(cal,{'a':'2003-01-11'})[1:].any()


def test_multiple_obligations_all_need_termination():
    cal=pd.date_range('2003-01-10',periods=6)
    assert not halt_mask(cal,{'a':'2003-01-11','b':'2003-01-12'},{'a':'2003-01-13'})[2:].any()


def test_invalid_chronology_and_duplicate_calendar_fail():
    with pytest.raises(ValueError):halt_mask(['2003-01-10']*2,{})
    with pytest.raises(ValueError):halt_mask(['2003-01-10'],{'a':'2003-01-10'},{'a':'2003-01-09'})
