import * as React from 'react';

type Row = { symbol: string; sector?: string; score?: number; weight: number; reasons?: string[] };

export default function HoldingsTable({ rows }: { rows: Row[] }) {
  return (
    <div className="table-holder">
      <table style={{ width:'100%', color:'#ddd', borderCollapse:'collapse' }}>
        <thead>
          <tr>
            <th style={{textAlign:'left'}}>Symbol</th>
            <th style={{textAlign:'left'}}>Sector</th>
            <th style={{textAlign:'right'}}>Score</th>
            <th style={{textAlign:'right'}}>Weight</th>
            <th style={{textAlign:'left'}}>Reasons</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
              <tr key={r.symbol + '-' + i} style={{borderTop: '1px solid #333'}}>
                <td>{r.symbol}</td>
                <td>{r.sector || '—'}</td>
                <td style={{textAlign: 'right'}}>{r.score?.toFixed?.(2) ?? '—'}</td>
                <td style={{textAlign: 'right'}}>{(r.weight * 100).toFixed(2)}%</td>
                <td>{(r.reasons ?? []).join(' | ')}</td>
              </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
