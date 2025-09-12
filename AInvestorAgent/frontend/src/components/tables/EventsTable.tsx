import React from "react";

type EventRow = { time: string; level: "INFO" | "WARN" | "ERROR"; module: string; msg: string };

const EventsTable: React.FC<{ rows: EventRow[] }> = ({ rows }) => {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>时间</th>
          <th>级别</th>
          <th>模块</th>
          <th>消息</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td>{r.time}</td>
            <td>{r.level}</td>
            <td>{r.module}</td>
            <td>{r.msg}</td>
          </tr>
        ))}
        {!rows.length && (
          <tr>
            <td colSpan={4}>
              <div className="empty">暂无事件</div>
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
};

export default EventsTable;
