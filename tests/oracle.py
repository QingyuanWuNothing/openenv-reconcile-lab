"""Independent SQL solutions used only by tests; excluded from runtime images."""

QUERIES = {
    "finance": """
    WITH ranked AS (
      SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY version DESC) rn FROM events
    ), paid AS (
      SELECT invoice_id, SUM(CASE WHEN kind='payment' THEN amount ELSE -amount END) net
      FROM ranked WHERE rn=1 AND status='posted' AND day<=:cutoff_day GROUP BY invoice_id
    ), balances AS (
      SELECT MAX(0, i.amount-COALESCE(p.net,0)) balance, f.usd_rate, c.region
      FROM invoices i JOIN customers c USING(customer_id) JOIN fx f USING(currency)
      LEFT JOIN paid p USING(invoice_id)
      WHERE i.status='approved' AND i.issued_day<=:cutoff_day
    )
    SELECT ROUND(SUM(balance*usd_rate),2) outstanding_usd,
      ROUND(SUM(CASE WHEN region='north' THEN balance*usd_rate ELSE 0 END),2) north_outstanding_usd,
      SUM(CASE WHEN balance>0 THEN 1 ELSE 0 END) unpaid_invoices FROM balances
    """,
    "science": """
    WITH latest AS (
      SELECT *, ROW_NUMBER() OVER (PARTITION BY sample_id,replicate_id ORDER BY revision DESC) rn
      FROM readings
    ), means AS (
      SELECT s.sample_id, s.arm, AVG((r.raw-b.offset)*1.0/b.gain) sample_mean
      FROM samples s JOIN batches b USING(batch_id) JOIN latest r USING(sample_id)
      WHERE s.excluded=0 AND b.qc='pass' AND r.rn=1 AND r.valid=1 GROUP BY s.sample_id,s.arm
    )
    SELECT ROUND(AVG(CASE WHEN arm='treatment' THEN sample_mean END),2) treatment_mean,
      ROUND(AVG(CASE WHEN arm='control' THEN sample_mean END),2) control_mean,
      COUNT(*) eligible_samples FROM means
    """,
    "office": """
    WITH ranked AS (
      SELECT *, ROW_NUMBER() OVER (PARTITION BY ticket_id,event_seq ORDER BY revision DESC) rn
      FROM events
    ), timeline AS (
      SELECT ticket_id, minute, state FROM ranked WHERE rn=1 AND minute<=:audit_minute
      UNION ALL SELECT ticket_id, opened_minute, 'active' FROM tickets
    ), intervals AS (
      SELECT *, LEAD(minute,1,:audit_minute) OVER (PARTITION BY ticket_id ORDER BY minute) until,
        ROW_NUMBER() OVER (PARTITION BY ticket_id ORDER BY minute DESC) last_row FROM timeline
    ), age AS (
      SELECT ticket_id, SUM(CASE WHEN state='active' THEN until-minute ELSE 0 END) active,
        MAX(CASE WHEN last_row=1 AND state!='closed' THEN 1 ELSE 0 END) is_open
      FROM intervals GROUP BY ticket_id
    )
    SELECT SUM(is_open) open_tickets,
      SUM(CASE WHEN is_open=1 AND active>sla_minutes*1.0/(CASE WHEN priority='urgent' THEN 2 ELSE 1 END)
        THEN 1 ELSE 0 END) breached_tickets,
      SUM(active) total_active_minutes
      FROM age JOIN tickets USING(ticket_id) JOIN teams USING(team_id)
    """,
}


def oracle_sql(family, parameters):
    sql = QUERIES[family]
    for key, value in parameters.items():
        sql = sql.replace(":" + key, str(int(value)))
    return sql
