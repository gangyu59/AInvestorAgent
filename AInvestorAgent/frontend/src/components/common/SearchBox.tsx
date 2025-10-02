import { useState, useRef, useEffect } from 'react';

interface SearchBoxProps {
  watchlist?: string[];
}

export function SearchBox({ watchlist = [] }: SearchBoxProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [filteredList, setFilteredList] = useState<string[]>([]);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 过滤 watchlist
  useEffect(() => {
    if (query.trim()) {
      const filtered = watchlist.filter(symbol =>
        symbol.toUpperCase().includes(query.toUpperCase())
      );
      setFilteredList(filtered);
      setIsOpen(filtered.length > 0);
    } else {
      setFilteredList(watchlist);
      setIsOpen(false);
    }
  }, [query, watchlist]);

  // 点击外部关闭下拉框
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = () => {
    if (query.trim()) {
      window.location.hash = `#/stock?query=${query.trim().toUpperCase()}`;
      setIsOpen(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleSelect = (symbol: string) => {
    setQuery(symbol);
    window.location.hash = `#/stock?query=${symbol}`;
    setIsOpen(false);
  };

  const handleInputFocus = () => {
    if (watchlist.length > 0) {
      setFilteredList(watchlist);
      setIsOpen(true);
    }
  };

  return (
    <div className="search-box-container" ref={dropdownRef}>
      <div className="search-box-input-group">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={handleInputFocus}
          onKeyPress={handleKeyPress}
          placeholder="搜索股票代码..."
          className="search-box-input"
        />
        <button onClick={handleSearch} className="search-box-button">
          搜索
        </button>
      </div>

      {isOpen && filteredList.length > 0 && (
        <div className="search-dropdown">
          {filteredList.map((symbol) => (
            <div
              key={symbol}
              className="search-dropdown-item"
              onClick={() => handleSelect(symbol)}
            >
              {symbol}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}