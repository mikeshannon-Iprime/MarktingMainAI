export function FormField({
  label,
  error,
  hint,
  required = false,
  children,
  className = '',
}) {
  return (
    <label className={`form-field${error ? ' has-error' : ''}${className ? ` ${className}` : ''}`}>
      <span className="form-field-label">
        {label}
        {required ? <span className="required-mark" aria-hidden="true"> *</span> : null}
      </span>
      {children}
      {error ? <span className="field-error" role="alert">{error}</span> : null}
      {!error && hint ? <span className="field-hint">{hint}</span> : null}
    </label>
  )
}
