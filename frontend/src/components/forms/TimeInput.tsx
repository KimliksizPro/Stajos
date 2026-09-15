import React from 'react';

interface TimeInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'value'> {
  label?: string;
  value: string; // HH:MM format
  onChange: (value: string) => void;
  error?: string;
}

export const TimeInput: React.FC<TimeInputProps> = ({
  label,
  value,
  onChange,
  error,
  className = '',
  required,
  ...props
}) => {
  return (
    <div className="w-full flex flex-col gap-1">
      {label && (
        <label className="text-sm font-medium text-text-primary">
          {label} {required && <span className="text-error">*</span>}
        </label>
      )}
      <input
        type="time"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`w-full px-3 py-2 bg-white border ${
          error ? 'border-error' : 'border-border'
        } rounded-md text-text-primary focus:outline-none focus:ring-2 focus:ring-accent focus:border-border-focus transition-colors ${className}`}
        required={required}
        {...props}
      />
      {error && <span className="text-sm text-error">{error}</span>}
    </div>
  );
};
