import type { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonProps = {
  label?: string;
  children?: ReactNode;
} & ButtonHTMLAttributes<HTMLButtonElement>;

export function Button({ label, children, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      {...rest}
      style={{
        padding: "0.5rem 1rem",
        borderRadius: "999px",
        border: "1px solid #111827",
        backgroundColor: "#111827",
        color: "#f9fafb",
        cursor: "pointer",
        fontSize: "0.875rem",
        fontWeight: 500,
      }}
    >
      {children ?? label}
    </button>
  );
}

