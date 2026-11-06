import { useEffect, useState } from 'react'
import api, { errMsg } from '../api'

export function TagInput({ value, onChange, placeholder }) {
  const [text, setText] = useState((value || []).join(', '))
  const change = (t) => {
    setText(t)
    onChange(t.split(',').map((s) => s.trim()).filter(Boolean))
  }
  return <input className="input" value={text} placeholder={placeholder || 'Separate with commas'} onChange={(e) => change(e.target.value)} />
}

/** Convert form state into an API payload (JSON, or FormData when a file field is present). */
export function buildPayload(values, fields) {
  const hasFile = fields.some((f) => f.type === 'file')
  const out = hasFile ? new FormData() : {}
  const put = (k, v) => (hasFile ? out.append(k, typeof v === 'boolean' ? String(v) : v) : (out[k] = v))
  for (const f of fields) {
    let v = values[f.name]
    if (f.type === 'file') {
      if (v instanceof File) put(f.name, v)
      continue
    }
    if (v === undefined) continue
    if (v === '' || v === null) {
      if (['number', 'date'].includes(f.type) || (f.type === 'select' && f.nullable)) {
        if (f.nullable && !hasFile) put(f.name, null)
        continue
      }
      v = ''
    }
    if (hasFile && Array.isArray(v)) v = JSON.stringify(v)
    put(f.name, v)
  }
  return out
}

export function FormFields({ fields, values, set }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {fields.map((f) => {
        if (f.hideIf?.(values)) return null
        const v = values[f.name]
        let input
        if (f.type === 'select') {
          input = (
            <select id={f.name} className="input" value={v ?? ''} required={f.required} onChange={(e) => set(f.name, e.target.value)}>
              <option value="">Select…</option>
              {f.options.map(([val, lab]) => <option key={val} value={val}>{lab}</option>)}
            </select>
          )
        } else if (f.type === 'textarea') {
          input = <textarea id={f.name} rows={f.rows || 4} className="input" value={v ?? ''} required={f.required} onChange={(e) => set(f.name, e.target.value)} />
        } else if (f.type === 'checkbox') {
          input = (
            <label className="flex items-center gap-2 text-sm font-semibold">
              <input type="checkbox" checked={!!v} onChange={(e) => set(f.name, e.target.checked)} /> {f.label}
            </label>
          )
        } else if (f.type === 'tags') {
          input = <TagInput value={v} onChange={(arr) => set(f.name, arr)} placeholder={f.placeholder} />
        } else if (f.type === 'file') {
          input = (
            <div className="text-sm">
              {typeof v === 'string' && v && <a className="mr-3 underline" href={v} target="_blank" rel="noreferrer">View current file</a>}
              <input id={f.name} type="file" onChange={(e) => set(f.name, e.target.files[0])} />
            </div>
          )
        } else {
          input = (
            <>
              <input id={f.name} type={f.type || 'text'} className="input" value={v ?? ''} required={f.required} min={f.min} list={f.datalist ? `${f.name}-list` : undefined} placeholder={f.placeholder} onChange={(e) => set(f.name, e.target.value)} />
              {f.datalist && <datalist id={`${f.name}-list`}>{f.datalist.map((d) => <option key={d} value={d} />)}</datalist>}
            </>
          )
        }
        return (
          <div key={f.name} className={f.full ? 'sm:col-span-2' : ''}>
            {f.type !== 'checkbox' && (
              <label className="label" htmlFor={f.name}>
                {f.label}
                {f.tip && <span tabIndex={0} role="img" aria-label={f.tip} title={f.tip} className="ml-1 cursor-help text-teal-light">ⓘ</span>}
              </label>
            )}
            {input}
            {f.hint && <p className="mt-1 text-xs text-teal-soft">{f.hint}</p>}
          </div>
        )
      })}
    </div>
  )
}

export function Alert({ kind = 'error', children }) {
  if (!children) return null
  const style = kind === 'error' ? 'bg-red-50 border-red-300 text-red-900' : 'bg-green-50 border-green-300 text-green-900'
  return <div role={kind === 'error' ? 'alert' : 'status'} className={`rounded-md border px-3 py-2 text-sm ${style}`}>{children}</div>
}

export function Chip({ children, className = '' }) {
  return <span className={`inline-block rounded-full bg-beige-dark px-2.5 py-0.5 text-xs font-semibold ${className}`}>{children}</span>
}

export function VerifyChip({ status }) {
  const map = { verified: 'bg-green-100 text-green-900', pending: 'bg-yellow-100 text-yellow-900', rejected: 'bg-red-100 text-red-900' }
  const text = { verified: 'Verified', pending: 'Verification pending', rejected: 'Not verified' }
  return <Chip className={map[status]}>{text[status] || status}</Chip>
}

export function Modal({ title, onClose, children }) {
  useEffect(() => {
    const h = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-teal/60 p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-modal="true" aria-label={title} className="mt-10 w-full max-w-xl rounded-lg bg-beige p-6 shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 className="text-xl font-bold">{title}</h2>
          <button onClick={onClose} className="text-sm font-semibold underline">Close</button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function FileUpload({ label, endpoint, field, url, onDone, accept }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const pick = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setBusy(true)
    setErr('')
    const fd = new FormData()
    fd.append(field, file)
    try {
      const r = await api.patch(endpoint, fd)
      onDone?.(r.data)
    } catch (x) {
      setErr(errMsg(x))
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="text-sm">
      <span className="label">{label}</span>
      {url && <a className="mr-3 underline" href={url} target="_blank" rel="noreferrer">View current file</a>}
      <input type="file" accept={accept} onChange={pick} disabled={busy} />
      {busy && <span className="ml-2">Uploading…</span>}
      {err && <p className="mt-1 text-red-800">{err}</p>}
    </div>
  )
}

/** Generic list + add/edit/delete section backed by a REST endpoint. */
export function CrudSection({ title, hint, endpoint, fields, summary, emptyText, onChange }) {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const load = () => api.get(endpoint).then((r) => setItems(r.data))
  useEffect(() => { load() }, [])
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const save = async (e) => {
    e.preventDefault()
    setBusy(true)
    setErr('')
    try {
      const payload = buildPayload(form, fields)
      if (form.id) await api.patch(`${endpoint}${form.id}/`, payload)
      else await api.post(endpoint, payload)
      setForm(null)
      await load()
      onChange?.()
    } catch (x) {
      setErr(errMsg(x))
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id) => {
    if (!window.confirm('Delete this entry?')) return
    await api.delete(`${endpoint}${id}/`)
    await load()
    onChange?.()
  }

  return (
    <section className="card">
      <div className="mb-3 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold">{title}</h2>
          {hint && <p className="text-sm text-teal-soft">{hint}</p>}
        </div>
        {!form && <button className="btn-outline shrink-0" onClick={() => setForm({})}>Add {title.toLowerCase().replace(/s$/, '')}</button>}
      </div>

      {items.length === 0 && !form && <p className="text-sm text-teal-soft">{emptyText}</p>}
      <ul className="divide-y divide-beige-line">
        {items.map((it) => (
          <li key={it.id} className="flex items-start justify-between gap-4 py-3">
            <div className="text-sm">{summary(it)}</div>
            <div className="flex shrink-0 gap-4 text-sm">
              <button className="font-semibold underline" onClick={() => setForm(it)}>Edit</button>
              <button className="btn-danger" onClick={() => remove(it.id)}>Delete</button>
            </div>
          </li>
        ))}
      </ul>

      {form && (
        <form key={form.id ?? 'new'} onSubmit={save} className="mt-4 space-y-4 rounded-md bg-beige-dark/60 p-4">
          <FormFields fields={fields} values={form} set={set} />
          <Alert>{err}</Alert>
          <div className="flex gap-3">
            <button className="btn" disabled={busy}>{busy ? 'Saving…' : 'Save'}</button>
            <button type="button" className="btn-outline" onClick={() => { setForm(null); setErr('') }}>Cancel</button>
          </div>
        </form>
      )}
    </section>
  )
}
