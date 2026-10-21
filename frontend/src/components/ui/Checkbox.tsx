import type { InputHTMLAttributes, ReactNode } from 'react'

type CheckboxProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & { id: string; children: ReactNode }
export function Checkbox({ id, children, ...props }: CheckboxProps) {
  return <label className="check-row" htmlFor={id}><input id={id} type="checkbox" {...props}/><span>{children}</span></label>
}
