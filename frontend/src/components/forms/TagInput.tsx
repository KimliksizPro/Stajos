import React, { useState, type KeyboardEvent } from 'react';
import { X } from 'lucide-react';

interface TagInputProps {
  label?: string;
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  suggestions?: string[];
}

export const TagInput: React.FC<TagInputProps> = ({
  label,
  tags,
  onChange,
  placeholder = 'Etiket ekle...',
}) => {
  const [inputValue, setInputValue] = useState('');

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const newTag = inputValue.trim();
      if (newTag && !tags.includes(newTag)) {
        onChange([...tags, newTag]);
      }
      setInputValue('');
    } else if (e.key === 'Backspace' && !inputValue && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  };

  const removeTag = (indexToRemove: number) => {
    onChange(tags.filter((_, index) => index !== indexToRemove));
  };

  return (
    <div className="w-full flex flex-col gap-1">
      {label && <label className="text-sm font-medium text-text-primary">{label}</label>}
      <div className="flex flex-wrap items-center gap-2 p-2 bg-white border border-border rounded-md focus-within:border-border-focus focus-within:ring-2 focus-within:ring-accent transition-colors min-h-[42px]">
        {tags.map((tag, index) => (
          <span
            key={index}
            className="flex items-center gap-1 px-2.5 py-1 bg-accent-light text-accent rounded-sm text-sm"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(index)}
              className="hover:text-accent-hover focus:outline-none"
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={tags.length === 0 ? placeholder : ''}
          className="flex-1 min-w-[120px] outline-none bg-transparent text-sm text-text-primary placeholder:text-text-muted"
        />
      </div>
    </div>
  );
};
