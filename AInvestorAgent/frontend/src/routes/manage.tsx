export default function ManagePage() {
  return (
    <div className="page">
      <h2>管理与配置</h2>
      <div className="field">
        <label>单票权重上限</label>
        <input defaultValue="0.30" />
      </div>
      <div className="field">
        <label>行业权重上限</label>
        <input defaultValue="0.50" />
      </div>
      <div className="hint">此页先占位：后续接你的后端配置接口 /rules</div>
    </div>
  );
}
