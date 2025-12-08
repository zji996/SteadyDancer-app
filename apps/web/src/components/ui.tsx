import type { ReactNode } from "react";

interface CardProps {
    children: ReactNode;
    className?: string;
    onClick?: () => void;
    hoverable?: boolean;
}

export function Card({
    children,
    className = "",
    onClick,
    hoverable = false,
}: CardProps) {
    return (
        <div
            className={`glass rounded-xl p-5 ${hoverable ? "glass-hover cursor-pointer" : ""
                } ${className}`}
            onClick={onClick}
        >
            {children}
        </div>
    );
}

interface ButtonProps {
    children: ReactNode;
    onClick?: () => void;
    variant?: "primary" | "secondary" | "ghost" | "danger";
    size?: "sm" | "md" | "lg";
    disabled?: boolean;
    className?: string;
    type?: "button" | "submit";
}

export function Button({
    children,
    onClick,
    variant = "primary",
    size = "md",
    disabled = false,
    className = "",
    type = "button",
}: ButtonProps) {
    const baseStyles =
        "font-medium rounded-lg transition-all duration-150 inline-flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed";

    const variants = {
        primary:
            "gradient-primary text-white hover:shadow-lg hover:shadow-primary-500/25",
        secondary:
            "bg-surface-200 text-gray-100 hover:bg-surface-300 border border-white/10",
        ghost: "text-gray-400 hover:text-white hover:bg-white/5",
        danger: "bg-error-500/20 text-error-500 hover:bg-error-500/30",
    };

    const sizes = {
        sm: "px-3 py-1.5 text-sm",
        md: "px-4 py-2 text-sm",
        lg: "px-6 py-3 text-base",
    };

    return (
        <button
            type={type}
            onClick={onClick}
            disabled={disabled}
            className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
        >
            {children}
        </button>
    );
}

interface BadgeProps {
    children: ReactNode;
    variant?: "default" | "success" | "warning" | "error" | "info";
}

export function Badge({ children, variant = "default" }: BadgeProps) {
    const variants = {
        default: "bg-gray-500/20 text-gray-300",
        success: "bg-success-500/20 text-success-500",
        warning: "bg-warning-500/20 text-warning-500",
        error: "bg-error-500/20 text-error-500",
        info: "bg-primary-500/20 text-primary-400",
    };

    return (
        <span
            className={`px-2 py-0.5 text-xs font-medium rounded-full ${variants[variant]}`}
        >
            {children}
        </span>
    );
}

interface InputProps {
    label?: string;
    placeholder?: string;
    value: string;
    onChange: (value: string) => void;
    type?: "text" | "number";
    multiline?: boolean;
    rows?: number;
    className?: string;
}

export function Input({
    label,
    placeholder,
    value,
    onChange,
    type = "text",
    multiline = false,
    rows = 3,
    className = "",
}: InputProps) {
    const inputStyles =
        "w-full bg-surface-200 border border-white/10 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/50 transition-colors";

    return (
        <div className={`space-y-1.5 ${className}`}>
            {label && (
                <label className="block text-sm font-medium text-gray-300">
                    {label}
                </label>
            )}
            {multiline ? (
                <textarea
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    placeholder={placeholder}
                    rows={rows}
                    className={`${inputStyles} resize-none`}
                />
            ) : (
                <input
                    type={type}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    placeholder={placeholder}
                    className={inputStyles}
                />
            )}
        </div>
    );
}

interface SelectProps {
    label?: string;
    value: string;
    onChange: (value: string) => void;
    options: { value: string; label: string }[];
    placeholder?: string;
    className?: string;
}

export function Select({
    label,
    value,
    onChange,
    options,
    placeholder,
    className = "",
}: SelectProps) {
    return (
        <div className={`space-y-1.5 ${className}`}>
            {label && (
                <label className="block text-sm font-medium text-gray-300">
                    {label}
                </label>
            )}
            <select
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="w-full bg-surface-200 border border-white/10 rounded-lg px-4 py-2.5 text-gray-100 focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/50 transition-colors"
            >
                {placeholder && (
                    <option value="" disabled>
                        {placeholder}
                    </option>
                )}
                {options.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                        {opt.label}
                    </option>
                ))}
            </select>
        </div>
    );
}

interface LoadingSpinnerProps {
    size?: "sm" | "md" | "lg";
}

export function LoadingSpinner({ size = "md" }: LoadingSpinnerProps) {
    const sizes = {
        sm: "w-4 h-4",
        md: "w-6 h-6",
        lg: "w-8 h-8",
    };

    return (
        <div
            className={`${sizes[size]} border-2 border-primary-500/20 border-t-primary-500 rounded-full animate-spin`}
        />
    );
}

interface EmptyStateProps {
    title: string;
    description: string;
    action?: ReactNode;
    icon?: ReactNode;
}

export function EmptyState({
    title,
    description,
    action,
    icon,
}: EmptyStateProps) {
    return (
        <div className="flex flex-col items-center justify-center py-12 text-center">
            {icon && <div className="mb-4 text-gray-500">{icon}</div>}
            <h3 className="text-lg font-medium text-gray-200 mb-1">{title}</h3>
            <p className="text-sm text-gray-400 mb-4 max-w-sm">{description}</p>
            {action}
        </div>
    );
}

interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    children: ReactNode;
}

export function Modal({ isOpen, onClose, title, children }: ModalProps) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal Content */}
            <div className="relative glass rounded-2xl p-6 w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-white">{title}</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-white transition-colors"
                    >
                        <svg
                            className="w-5 h-5"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M6 18L18 6M6 6l12 12"
                            />
                        </svg>
                    </button>
                </div>
                {children}
            </div>
        </div>
    );
}
