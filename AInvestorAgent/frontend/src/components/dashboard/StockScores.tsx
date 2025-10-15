export function StockScores({ scores }: { scores: any[] }) {
  const items = (scores || []).slice(0, 8);

  return (
    <div className="dashboard-card stock-scores">
      <div className="dashboard-card-header">
        <h3 className="dashboard-card-title">股票池评分</h3>
        <button onClick={() => (window.location.hash = "#/stock")}>查看更多 →</button>
      </div>

      <div className="dashboard-card-body">
        {/* 表头 - 调整列宽对齐 */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '80px 100px 80px 80px',
          gap: '8px',
          padding: '8px 12px',
          background: 'rgba(255,255,255,0.03)',
          borderRadius: '6px 6px 0 0',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          alignItems: 'center'
        }}>
          <span style={{ color: '#9ca3af', fontSize: '12px', fontWeight: 600 }}>代码</span>
          <span style={{ color: '#9ca3af', fontSize: '12px', fontWeight: 600, textAlign: 'center' }}>评分分布</span>
          <span style={{ color: '#9ca3af', fontSize: '12px', fontWeight: 600, textAlign: 'center' }}>总分</span>
          <span style={{ color: '#9ca3af', fontSize: '12px', fontWeight: 600, textAlign: 'center' }}>操作</span>
        </div>

        {/* 滚动区域 - 深色主题优化 */}
        <div className="scores-scroll" style={{
          maxHeight: '320px',
          overflowY: 'auto',
          overflowX: 'hidden',
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgba(255,255,255,0.15) transparent'
        }}>
          <style>{`
            .scores-scroll::-webkit-scrollbar {
              width: 6px;
            }
            .scores-scroll::-webkit-scrollbar-track {
              background: transparent;
            }
            .scores-scroll::-webkit-scrollbar-thumb {
              background: rgba(255,255,255,0.15);
              border-radius: 3px;
            }
            .scores-scroll::-webkit-scrollbar-thumb:hover {
              background: rgba(255,255,255,0.25);
            }
          `}</style>

          {items.map((item) => {
            // 提取因子数据
            const factors = item.score?.factors || item.factors || {};
            // 兼容两种字段名格式
            const factorValues = {
              value: factors.value ?? factors.f_value ?? 0,
              quality: factors.quality ?? factors.f_quality ?? 0,
              momentum: factors.momentum ?? factors.f_momentum ?? 0,
              sentiment: factors.sentiment ?? factors.f_sentiment ?? 0,
              risk: factors.risk ?? factors.f_risk ?? 0
            };

            return (
              <div
                key={item.symbol}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '80px 100px 80px 80px',
                  gap: '8px',
                  padding: '10px 12px',
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  transition: 'background 0.2s ease',
                  alignItems: 'center'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <span style={{
                  fontWeight: 600,
                  color: '#e5e7eb',
                  fontSize: '13px'
                }}>
                  {item.symbol}
                </span>

                {/* 迷你雷达图 - 修复显示 */}
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <svg width="60" height="60" viewBox="0 0 60 60">
                    {(() => {
                      // 使用5个因子（去掉growth和news，保留主要4个+risk）
                      const order = ["value", "quality", "momentum", "sentiment"];
                      const vals = order.map((k) => {
                        const v = factorValues[k];
                        // 归一化到0-1范围
                        return Math.max(0, Math.min(1, typeof v === 'number' ? v : 0));
                      });

                      const cx = 30, cy = 30, r = 22, n = order.length;

                      // 背景网格（3层）
                      const gridLevels = [1, 0.66, 0.33];

                      // 计算多边形点
                      const points = vals
                        .map((v, i) => {
                          const angle = -Math.PI / 2 + (i * 2 * Math.PI) / n;
                          const radius = r * v;
                          const x = cx + radius * Math.cos(angle);
                          const y = cy + radius * Math.sin(angle);
                          return `${x},${y}`;
                        })
                        .join(" ");

                      // 轴线点
                      const axisPoints = order.map((_, i) => {
                        const angle = -Math.PI / 2 + (i * 2 * Math.PI) / n;
                        const x = cx + r * Math.cos(angle);
                        const y = cy + r * Math.sin(angle);
                        return { x, y };
                      });

                      return (
                        <g>
                          {/* 背景网格圆 */}
                          {gridLevels.map((level, idx) => (
                            <circle
                              key={idx}
                              cx={cx}
                              cy={cy}
                              r={r * level}
                              fill="none"
                              stroke="rgba(255,255,255,0.08)"
                              strokeWidth="0.5"
                            />
                          ))}

                          {/* 轴线 */}
                          {axisPoints.map((point, idx) => (
                            <line
                              key={idx}
                              x1={cx}
                              y1={cy}
                              x2={point.x}
                              y2={point.y}
                              stroke="rgba(255,255,255,0.05)"
                              strokeWidth="0.5"
                            />
                          ))}

                          {/* 数据多边形 */}
                          <polygon
                            points={points}
                            fill="rgba(59, 130, 246, 0.25)"
                            stroke="#3b82f6"
                            strokeWidth="1.5"
                          />

                          {/* 数据点 */}
                          {vals.map((v, i) => {
                            const angle = -Math.PI / 2 + (i * 2 * Math.PI) / n;
                            const radius = r * v;
                            const x = cx + radius * Math.cos(angle);
                            const y = cy + radius * Math.sin(angle);
                            return (
                              <circle
                                key={i}
                                cx={x}
                                cy={y}
                                r="2"
                                fill="#60a5fa"
                                stroke="#3b82f6"
                                strokeWidth="1"
                              />
                            );
                          })}
                        </g>
                      );
                    })()}
                  </svg>
                </div>

                {/* 总分 - 深色主题优化 */}
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <span
                    style={{
                      fontWeight: 700,
                      fontSize: '15px',
                      padding: '4px 10px',
                      borderRadius: '4px',
                      background: item.score?.score >= 80 ? 'rgba(16, 185, 129, 0.15)' :
                                  item.score?.score >= 70 ? 'rgba(59, 130, 246, 0.15)' :
                                  'rgba(107, 114, 128, 0.15)',
                      color: item.score?.score >= 80 ? '#10b981' :
                             item.score?.score >= 70 ? '#60a5fa' :
                             '#9ca3af',
                      border: `1px solid ${
                        item.score?.score >= 80 ? 'rgba(16, 185, 129, 0.3)' : 
                        item.score?.score >= 70 ? 'rgba(59, 130, 246, 0.3)' : 
                        'rgba(107, 114, 128, 0.2)'
                      }`,
                      minWidth: '48px',
                      textAlign: 'center'
                    }}
                  >
                    {item.score?.score ? item.score.score.toFixed(1) : "--"}
                  </span>
                </div>

                {/* 操作按钮 - 深色主题 */}
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <button
                    onClick={() => (window.location.hash = `#/stock?query=${item.symbol}`)}
                    style={{
                      fontSize: '12px',
                      padding: '4px 12px',
                      borderRadius: '6px',
                      border: '1px solid rgba(255,255,255,0.1)',
                      background: 'rgba(255,255,255,0.05)',
                      color: '#d1d5db',
                      transition: 'all 0.2s ease',
                      cursor: 'pointer'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(255,255,255,0.1)';
                      e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)';
                      e.currentTarget.style.color = '#f3f4f6';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                      e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
                      e.currentTarget.style.color = '#d1d5db';
                    }}
                  >
                    详情
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}