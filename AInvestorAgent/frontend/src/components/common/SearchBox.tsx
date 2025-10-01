import { useState, useMemo } from 'react';

export function SearchBox({ watchlist }: { watchlist: string[] }) {
  const [query, setQuery] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);

  const suggestions = useMemo(() => {
    if (query.length === 0) return (watchlist || []).slice(0, 20).map(s => ({ symbol: s }));
    return (watchlist || []).filter(s => s.toLowerCase().includes(query.toLowerCase())).slice(0, 10).map(s => ({ symbol: s }));
  }, [query, watchlist]);

  const handleSelect = (symbol: string) => {
    window.location.hash = `#/stock?query=${encodeURIComponent(symbol)}`;
    setShowDropdown(false);
    setQuery('');
  };

  const handleKeyDown = (e: any) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => Math.min(prev + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(prev - 1, -1));
    } else if (e.key === 'Enter') {
      if (selectedIndex >= 0) handleSelect(suggestions[selectedIndex].symbol);
      else if (query) handleSelect(query.toUpperCase());
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
    }
  };

  return (
    <div className="relative w-full">
      <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} onFocus={() => setShowDropdown(true)}
        onBlur={() => setTimeout(() => setShowDropdown(false), 200)} onKeyDown={handleKeyDown} placeholder="搜索股票代码..."
        className="w-full px-4 py-2 bg-[#1a1a2e] border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors" />
      {showDropdown && suggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-[#2d2d44] border border-gray-700 rounded-lg shadow-2xl max-h-80 overflow-y-auto z-50">
          {query.length === 0 && <div className="px-4 py-2 text-xs text-gray-500 border-b border-gray-700 font-medium">📌 我的关注列表（Top {suggestions.length}）</div>}
          {suggestions.map((stock, idx) => (
            <button key={stock.symbol} onClick={() => handleSelect(stock.symbol)}
              className={`w-full px-4 py-3 flex items-center justify-between hover:bg-gray-700 transition-colors text-left ${idx === selectedIndex ? 'bg-gray-700' : ''}`}>
              <div className="flex items-center gap-3">
                <span className="text-yellow-500">⭐</span>
                <span className="font-semibold text-white">{stock.symbol}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}