import { useEffect, useId, useMemo, useRef, useState } from 'react'
import api from '../api'

let cache = null // one fetch per page load; the list changes only when an admin verifies a university
const loadUniversities = () => (cache ||= api.get('/universities/').then((r) => r.data).catch((e) => { cache = null; throw e }))

/** Searchable dropdown (ARIA combobox) of verified universities. `value` is the university id. */
export default function UniversityPicker({ id, value, onChange, required }) {
  const [all, setAll] = useState(null)
  const [failed, setFailed] = useState(false)
  const [text, setText] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const box = useRef(null)
  const listId = useId()

  useEffect(() => { loadUniversities().then(setAll).catch(() => setFailed(true)) }, [])

  const selected = useMemo(() => all?.find((u) => String(u.id) === String(value)), [all, value])
  useEffect(() => { if (selected) setText(selected.name) }, [selected])

  const matches = useMemo(() => {
    const q = (open ? text : '').trim().toLowerCase()
    const list = all || []
    if (!q || (selected && text === selected.name)) return list.slice(0, 50)
    return list.filter((u) => `${u.name} ${u.city} ${u.state}`.toLowerCase().includes(q)).slice(0, 50)
  }, [all, text, open, selected])

  useEffect(() => {
    const away = (e) => { if (!box.current?.contains(e.target)) close() }
    document.addEventListener('mousedown', away)
    return () => document.removeEventListener('mousedown', away)
  })

  const close = () => { setOpen(false); setText(selected ? selected.name : '') }
  const pick = (u) => { onChange(u.id); setText(u.name); setOpen(false) }
  const onKey = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setActive((a) => Math.min(a + 1, matches.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)) }
    else if (e.key === 'Enter' && open && matches[active]) { e.preventDefault(); pick(matches[active]) }
    else if (e.key === 'Escape' && open) { e.stopPropagation(); close() }
  }

  return (
    <div className="relative" ref={box}>
      <input
        id={id} className="input pr-8" role="combobox" aria-expanded={open} aria-controls={listId} aria-autocomplete="list"
        aria-activedescendant={open && matches[active] ? `${listId}-${matches[active].id}` : undefined}
        autoComplete="off" placeholder={all ? 'Search for your university…' : 'Loading universities…'} disabled={failed}
        value={text}
        onFocus={() => setOpen(true)}
        onChange={(e) => { setText(e.target.value); setOpen(true); setActive(0) }}
        onKeyDown={onKey}
      />
      <span aria-hidden="true" className="pointer-events-none absolute right-3 top-2.5 text-xs text-teal-soft">▾</span>
      {/* Keeps native "required" validation working: empty until a university is actually chosen. */}
      {required && <input tabIndex={-1} aria-hidden="true" className="absolute bottom-0 left-1/2 h-px w-px opacity-0" required value={value || ''} onChange={() => {}} />}

      {open && (
        <ul id={listId} role="listbox" className="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-md border border-beige-line bg-white py-1 text-sm shadow-lg">
          {matches.map((u, i) => (
            <li
              key={u.id} id={`${listId}-${u.id}`} role="option" aria-selected={String(u.id) === String(value)}
              onMouseDown={(e) => { e.preventDefault(); pick(u) }} onMouseEnter={() => setActive(i)}
              className={`cursor-pointer px-3 py-2 ${i === active ? 'bg-beige-dark' : ''}`}
            >
              <span className="font-semibold">{u.name}</span>
              <span className="block text-xs text-teal-soft">{[u.city, u.state].filter(Boolean).join(', ')}{u.nirf_rank ? ` · NIRF #${u.nirf_rank}` : ''}</span>
            </li>
          ))}
          {all && matches.length === 0 && (
            <li className="px-3 py-3 text-teal-soft">
              No verified university matches. Only universities verified by Aeterna can sign degrees. Ask yours to register.
            </li>
          )}
        </ul>
      )}
      {failed && <p className="mt-1 text-xs text-red-800">Could not load the university list. Refresh the page.</p>}
    </div>
  )
}
