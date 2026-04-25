export const Validators = {
  email: (value: string): string | null => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!value) return 'Email is required';
    if (!emailRegex.test(value)) return 'Please enter a valid email address';
    return null;
  },

  password: (value: string): string | null => {
    if (!value) return 'Password is required';
    if (value.length < 8) return 'Password must be at least 8 characters';
    return null;
  },

  required: (label: string) => (value: string): string | null => {
    if (!value || value.trim() === '') return `${label} is required`;
    return null;
  },

  minLength: (min: number) => (value: string): string | null => {
    if (value.length < min) return `Must be at least ${min} characters`;
    return null;
  },

  maxLength: (max: number) => (value: string): string | null => {
    if (value.length > max) return `Must be at most ${max} characters`;
    return null;
  },

  phone: (value: string): string | null => {
    const phoneRegex = /^\+?[\d\s\-()]{10,}$/;
    if (!value) return null; // Optional
    if (!phoneRegex.test(value)) return 'Please enter a valid phone number';
    return null;
  },
};

export function runValidators(
  value: string,
  validators: Array<(value: string) => string | null>,
): string | null {
  for (const validator of validators) {
    const error = validator(value);
    if (error) return error;
  }
  return null;
}
