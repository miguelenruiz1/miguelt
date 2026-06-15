import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff, Check, X } from 'lucide-react'
import { useRegister } from '@/hooks/useAuth'

const schema = z.object({
  full_name: z.string().min(1, 'Nombre requerido').max(255),
  username: z.string().min(3, 'Mínimo 3 caracteres').max(100).regex(/^[a-zA-Z0-9._-]+$/, 'Solo letras, números, puntos, guiones'),
  email: z.string().email('Email inválido'),
  password: z.string().min(8, 'Mínimo 8 caracteres'),
  terms: z.literal(true, { errorMap: () => ({ message: 'Debes aceptar los términos' }) }),
})

type FormData = z.infer<typeof schema>

function getStrength(pw: string) {
  let s = 0
  if (pw.length >= 8) s++; if (pw.length >= 12) s++; if (/[A-Z]/.test(pw)) s++; if (/[0-9]/.test(pw)) s++; if (/[^A-Za-z0-9]/.test(pw)) s++
  if (s <= 1) return { s, l: 'Débil', c: '#FF4757' }; if (s <= 2) return { s, l: 'Regular', c: '#F5A623' }; if (s <= 3) return { s, l: 'Buena', c: '#FFBD2E' }; if (s <= 4) return { s, l: 'Fuerte', c: '#00C264' }
  return { s, l: 'Muy fuerte', c: '#00E87A' }
}

const Rule = ({ ok, text }: { ok: boolean; text: string }) => (
  <span className="flex items-center gap-1 text-xs" style={{ color: ok ? '#00E87A' : '#6B7A8D' }}>
    {ok ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}{text}
  </span>
)

const inputCls = "h-11 w-full rounded-lg border px-4 py-2.5 text-sm text-white placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-[#00E87A]/30"
const inputStyle = { background: '#141A22', borderColor: 'rgba(255,255,255,0.06)' }

export function RegisterPage() {
  const [showPw, setShowPw] = useState(false)
  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema), mode: 'onChange', defaultValues: { terms: false as any } })
  const reg = useRegister()
  const pw = watch('password') || ''
  const str = getStrength(pw)

  const onSubmit = (d: FormData) => reg.mutate({ email: d.email, username: d.username, full_name: d.full_name, password: d.password })

  return (
    <div className="min-h-screen flex" style={{ background: '#080B0F' }}>
      {/* Left — branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:60px_60px]" />
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[400px] rounded-full blur-3xl" style={{ background: 'radial-gradient(circle, rgba(0,232,122,0.15), transparent)' }} />

        <div className="relative z-10">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: '#00E87A' }}><span className="text-black font-extrabold text-sm">T</span></div>
            <span className="font-bold text-white text-xl">Trace<span style={{ color: '#00E87A' }}>Log</span></span>
          </div>
        </div>

        <div className="relative z-10 max-w-md">
          <h2 className="text-3xl font-extrabold text-white leading-tight mb-4">
            Empieza a controlar tu operación <span style={{ color: '#00E87A' }}>hoy</span>
          </h2>
          <p className="text-base leading-relaxed" style={{ color: '#6B7A8D' }}>
            Crea tu cuenta en 30 segundos. Te recomendamos los módulos ideales para tu industria.
          </p>
        </div>

        <div className="relative z-10 flex gap-8">
          {[{ n: '30s', l: 'Para empezar' }, { n: '6', l: 'Módulos' }, { n: '∞', l: 'Escalabilidad' }].map(s => (
            <div key={s.l}><div className="text-lg font-extrabold text-white">{s.n}</div><div className="text-xs" style={{ color: '#6B7A8D' }}>{s.l}</div></div>
          ))}
        </div>
      </div>

      {/* Right — form */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12 overflow-y-auto" style={{ background: '#0E1318' }}>
        <div className="w-full max-w-md">
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: '#00E87A' }}><span className="text-black font-extrabold text-sm">T</span></div>
            <span className="font-bold text-white text-xl">Trace<span style={{ color: '#00E87A' }}>Log</span></span>
          </div>

          <h1 className="text-2xl font-extrabold text-white mb-2">Crear cuenta</h1>
          <p className="text-sm mb-6" style={{ color: '#6B7A8D' }}>Completa tus datos para registrarte</p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div><label className="block text-sm font-medium text-gray-300 mb-1.5">Nombre completo *</label><input {...register('full_name')} className={inputCls} style={inputStyle} placeholder="Juan García" />{errors.full_name && <p className="mt-1 text-xs text-red-400">{errors.full_name.message}</p>}</div>
              <div><label className="block text-sm font-medium text-gray-300 mb-1.5">Usuario *</label><input {...register('username')} className={inputCls} style={inputStyle} placeholder="juan.garcia" />{errors.username && <p className="mt-1 text-xs text-red-400">{errors.username.message}</p>}</div>
            </div>
            <div><label className="block text-sm font-medium text-gray-300 mb-1.5">Email *</label><input {...register('email')} type="email" className={inputCls} style={inputStyle} placeholder="juan@empresa.com" />{errors.email && <p className="mt-1 text-xs text-red-400">{errors.email.message}</p>}</div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Contraseña *</label>
              <div className="relative">
                <input {...register('password')} type={showPw ? 'text' : 'password'} className={inputCls} style={inputStyle} placeholder="Mínimo 8 caracteres" />
                <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2">{showPw ? <Eye className="h-4 w-4 text-muted-foreground" /> : <EyeOff className="h-4 w-4 text-muted-foreground" />}</button>
              </div>
              {errors.password && <p className="mt-1 text-xs text-red-400">{errors.password.message}</p>}
              {pw.length > 0 && (
                <div className="mt-2 space-y-1.5">
                  <div className="flex gap-1">{[1,2,3,4,5].map(i => <div key={i} className="h-1.5 flex-1 rounded-full" style={{ background: i <= str.s ? str.c : '#141A22' }} />)}</div>
                  <p className="text-xs font-medium" style={{ color: str.c }}>{str.l}</p>
                  <div className="flex flex-wrap gap-x-4 gap-y-0.5">
                    <Rule ok={pw.length >= 8} text="8+ caracteres" /><Rule ok={/[A-Z]/.test(pw)} text="Mayúscula" /><Rule ok={/[0-9]/.test(pw)} text="Número" /><Rule ok={/[^A-Za-z0-9]/.test(pw)} text="Especial" />
                  </div>
                </div>
              )}
            </div>
            <div className="flex items-start gap-3">
              <input type="checkbox" {...register('terms')} className="mt-0.5 h-4 w-4 rounded border-gray-600 bg-transparent" />
              <p className="text-sm" style={{ color: '#6B7A8D' }}>Al crear una cuenta aceptas los <span className="text-white">Términos y Condiciones</span> y nuestra <span className="text-white">Política de Privacidad</span></p>
            </div>
            {errors.terms && <p className="text-xs text-red-400">{errors.terms.message}</p>}
            {reg.error && <div className="rounded-lg px-4 py-3 text-sm text-red-300" style={{ background: 'rgba(255,71,87,0.1)', border: '1px solid rgba(255,71,87,0.2)' }}>{reg.error.message}</div>}
            {reg.isSuccess && <div className="rounded-lg px-4 py-3 text-sm" style={{ background: 'rgba(0,232,122,0.1)', border: '1px solid rgba(0,232,122,0.2)', color: '#00E87A' }}>Cuenta creada. Redirigiendo...</div>}
            <button type="submit" disabled={reg.isPending} className="flex w-full items-center justify-center rounded-lg px-4 py-3 text-sm font-bold text-black transition hover:opacity-90 disabled:opacity-50" style={{ background: '#00E87A' }}>{reg.isPending ? 'Creando...' : 'Crear cuenta'}</button>
          </form>

          <p className="mt-6 text-sm text-center" style={{ color: '#6B7A8D' }}>
            ¿Ya tienes cuenta?{' '}<Link to="/login" className="font-semibold" style={{ color: '#00E87A' }}>Iniciar sesión</Link>
          </p>

        </div>
      </div>
    </div>
  )
}
