import { useState, useRef, useEffect } from "react";

interface MultiSelectProps {
  label: string;
  options: { label: string; value: string | number }[];
  value: (string | number)[];
  onChange: (value: (string | number)[]) => void;
  searchable?: boolean;
  placeholder?: string;
}

export function MultiSelect({
  label,
  options,
  value,
  onChange,
  searchable = false,
  placeholder = "Select...",
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch("");
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const filtered = options.filter((opt) =>
    String(opt.label).toLowerCase().includes(search.toLowerCase())
  );

  const toggle = (v: string | number) => {
    onChange(
      value.includes(v) ? value.filter((x) => x !== v) : [...value, v]
    );
  };

  const removeTag = (v: string | number, e: React.MouseEvent) => {
    e.stopPropagation();
    onChange(value.filter((x) => x !== v));
  };

  return (
    <div ref={ref} className="relative">
      <label className="mb-1 block text-xs font-medium text-gray-500 uppercase tracking-wider">
        {label}
      </label>
      <div
        onClick={() => setOpen(!open)}
        className="flex min-h-[38px] cursor-pointer flex-wrap items-center gap-1 rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-sm shadow-sm transition-colors hover:border-gray-300 focus-within:border-blue-400 focus-within:ring-1 focus-within:ring-blue-400"
      >
        {value.length === 0 && (
          <span className="text-gray-400">{placeholder}</span>
        )}
        {value.map((v) => (
          <span
            key={String(v)}
            className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700"
          >
            {String(options.find((o) => o.value === v)?.label ?? v)}
            <button
              onClick={(e) => removeTag(v, e)}
              className="ml-0.5 text-blue-400 hover:text-blue-600"
            >
              &times;
            </button>
          </span>
        ))}
      </div>

      {open && (
        <div className="absolute left-0 right-0 z-50 mt-1 max-h-60 overflow-auto rounded-lg border border-gray-200 bg-white shadow-lg">
          {searchable && (
            <div className="sticky top-0 border-b border-gray-100 bg-white p-2">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search..."
                className="w-full rounded-md border border-gray-200 px-2.5 py-1.5 text-sm outline-none focus:border-blue-400"
                autoFocus
              />
            </div>
          )}
          {filtered.length === 0 && (
            <div className="px-3 py-2 text-sm text-gray-400">
              No options
            </div>
          )}
          {filtered.map((opt) => (
            <div
              key={String(opt.value)}
              onClick={() => toggle(opt.value)}
              className={`flex cursor-pointer items-center gap-2 px-3 py-2 text-sm transition-colors hover:bg-gray-50 ${
                value.includes(opt.value) ? "bg-blue-50 text-blue-700" : "text-gray-700"
              }`}
            >
              <div
                className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                  value.includes(opt.value)
                    ? "border-blue-500 bg-blue-500"
                    : "border-gray-300"
                }`}
              >
                {value.includes(opt.value) && (
                  <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
              {String(opt.label)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
