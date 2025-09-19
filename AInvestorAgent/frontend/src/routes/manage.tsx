import { useEffect, useState } from "react";
import { getRules, updateRules, type Rules, triggerReport, listReports, type ReportInfo } from "../services/endpoints";

export default function ManagePage() {
  const [rules, setRules] = useState<Rules>({});
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string|null>(null);
  const [ok, setOk] = useState<string|null>(null);
  const [reports, setReports] = useState<ReportInfo[]>([]);
  const [genLoading, setGenLoading] = useState(false);

  async function load() {
    setErr(null);
    try { setRules(await getRules()); setReports(await listReports()); }
    catch (e:any) { setErr(e?.message || "加载失败"); }
  }
  useEffect(()=>{ load(); }, []);

  async function save() {
    setSaving(true); setErr(null); setOk(null);
    try { await updateRules(rules); setOk("已保存"); }
    catch (e:any) { setErr(e?.message || "保存失败"); }
    finally { setSaving(false); }
  }

  async function genReport() {
    setGenLoading(true); setErr(null); setOk(null);
    try { await triggerReport(); setOk("已触发生成"); setReports(await listReports()); }
    catch (e:any) { setErr(e?.message || "触发失败"); }
    finally { setGenLoading(false); }
  }

  return (
    <div className="page">
      <div className="page-header"><h2>管理与配置</h2></div>
      {err && <div className="card" style={{borderColor:"#ff6b6b"}}><div className="card-body">{err}</div></div>}
      {ok && <div className="card" style={{borderColor:"#2e7d32"}}><div className="card-body">{ok}</div></div>}

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><h3>风险约束</h3></div>
          <div className="card-body" style={{display:"grid", gridTemplateColumns:"180px 1fr", gap:10}}>
            <label>单票上限</label>
            <input value={rules["risk.max_stock"] ?? 0.3} onChange={e=>setRules({...rules, ["risk.max_stock"]: +e.target.value})} />
            <label>行业上限</label>
            <input value={rules["risk.max_sector"] ?? 0.5} onChange={e=>setRules({...rules, ["risk.max_sector"]: +e.target.value})} />
            <label>最小持仓</label>
            <input value={rules["risk.min_positions"] ?? 5} onChange={e=>setRules({...rules, ["risk.min_positions"]: +e.target.value})} />
            <label>最大持仓</label>
            <input value={rules["risk.max_positions"] ?? 15} onChange={e=>setRules({...rules, ["risk.max_positions"]: +e.target.value})} />
            <div></div>
            <div>
              <button className="btn btn-primary" onClick={save} disabled={saving}>{saving?"保存中…":"保存"}</button>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><h3>报告（日报/周报）</h3></div>
          <div className="card-body">
            <button className="btn" onClick={genReport} disabled={genLoading}>{genLoading?"触发中…":"生成报告"}</button>
            <ul className="list" style={{marginTop:10}}>
              {reports.map((r,i)=>(
                <li key={i}>
                  {r.created_at || r.name || r.id}
                  {r.url && <> · <a href={r.url} target="_blank" rel="noreferrer">查看</a></>}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
