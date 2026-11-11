import { forwardRef, type InputHTMLAttributes } from "react";

const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className = "", ...rest }, ref) {
    return (
      <input
        ref={ref}
        className={`w-full rounded-xl border border-border bg-white px-4 py-2.5 text-ink placeholder:text-ink-faint focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors ${className}`}
        {...rest}
      />
    );
  },
);

export default Input;
