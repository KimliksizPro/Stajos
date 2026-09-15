import React, { forwardRef } from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', required, ...props }, ref) => {
    return (
      <div className="w-full flex flex-col gap-1">
        {label && (
          <label className="text-sm font-medium text-text-primary">
            {label} {required && <span className="text-error">*</span>}
          </label>
        )}
        <input
          ref={ref}
          className={`w-full px-3 py-2 bg-white border ${
            error ? 'border-error' : 'border-border'
          } rounded-md text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent focus:border-border-focus transition-colors ${className}`}
          required={required}
          {...props}
        />
        {error && <span className="text-sm text-error">{error}</span>}
      </div>
    );
  }
);

Input.displayName = 'Input';
