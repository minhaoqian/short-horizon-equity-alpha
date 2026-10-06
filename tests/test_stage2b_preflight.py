import duckdb
import pytest
from src.evaluation.source_qa import validate_relations


def fixture():
    c=duckdb.connect()
    c.execute("CREATE TABLE f AS SELECT * FROM (VALUES (1,DATE '2020-01-02'),(2,DATE '2020-01-02'),(3,DATE '2020-01-02')) t(permno,signal_date)")
    c.execute("""CREATE TABLE labels AS SELECT * FROM (VALUES
        (1,DATE '2020-01-02','measurable_ordinary_event_adjusted',true,true),
        (2,DATE '2020-01-02','measurable_cash_only_delisting',true,true),
        (3,DATE '2020-01-02','valid_entry_unresolved_exit_wealth',false,NULL))
        t(permno,signal_date,label_status,numeric_label,finite_label)""")
    return c


def test_numeric_cash_delistings_preserved_and_unresolved_keys_retained():
    assert validate_relations(fixture(),3,2)=={'keys':3,'numeric_labels':2}


def test_duplicate_keys_fail_before_join():
    c=fixture();c.execute('INSERT INTO f SELECT * FROM f LIMIT 1')
    with pytest.raises(AssertionError):validate_relations(c,3,2)


def test_key_set_mismatch_fails_even_when_counts_match():
    c=fixture();c.execute('UPDATE f SET permno=4 WHERE permno=3')
    with pytest.raises(AssertionError):validate_relations(c,3,2)


def test_invented_numeric_unresolved_label_rejected():
    c=fixture();c.execute('UPDATE labels SET numeric_label=true,finite_label=true WHERE permno=3')
    with pytest.raises(AssertionError):validate_relations(c,3,3)
