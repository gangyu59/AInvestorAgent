import React from "react";
import type { TestRun } from "../../services/qa";

export default function RecentRunsTable({ runs }: { runs: TestRun[] }) {
  return (
    <div className="rounded-xl border border-gray-700 overflow-hidden">
      <table className="w-full text-sm bg-[#0f1115] text-white">
        <thead className="bg-[#141820]">
          <tr>
            <th className="p-2 text-left">时间</th>
            <th className="p-2 text-right">用例</th>
            <th className="p-2 text-right text-green-400">通过</th>
            <th className="p-2 text-right text-red-400">失败</th>
            <th className="p-2 text-right text-yellow-400">跳过</th>
            <th className="p-2 text-right">错误</th>
            <th className="p-2 text-right">通过率</th>
            <th className="p-2 text-right">耗时(s)</th>
            <th className="p-2">报告</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r, i) => (
            <tr key={i} className="border-t border-gray-800">
              <td className="p-2">{r.timestamp}</td>
              <td className="p-2 text-right">{r.stats.total}</td>
              <td className="p-2 text-right">{r.stats.passed}</td>
              <td className="p-2 text-right">{r.stats.failed}</td>
              <td className="p-2 text-right">{r.stats.skipped}</td>
              <td className="p-2 text-right">{r.stats.errors}</td>
              <td className="p-2 text-right">{r.pass_rate}%</td>
              <td className="p-2 text-right">{r.duration_sec}</td>
              <td className="p-2">
                {r.html_report ? <a className="underline" href={r.html_report} target="_blank" rel="noreferrer">HTML</a> : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
