import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff } from 'lucide-react'
import { useLogin } from '@/hooks/useAuth'

const schema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'Contraseña requerida'),
})
type FormData = z.infer<typeof schema>

export function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema) })
  const login = useLogin()
  const onSubmit = (data: FormData) => login.mutate(data)

  return (
    <div className="min-h-screen flex" style={{ background: '#080B0F' }}>
      {/* Left — branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:60px_60px]" />
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[400px] rounded-full blur-3xl" style={{ background: 'radial-gradient(circle, rgba(0,232,122,0.15), transparent)' }} />

        <div className="relative z-10">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: '#00E87A' }}>
              <span className="text-black font-extrabold text-sm">T</span>
            </div>
            <span className="font-bold text-white text-xl">Trace<span style={{ color: '#00E87A' }}>Log</span></span>
          </div>
        </div>

        <div className="relative z-10 max-w-md">
          <h2 className="text-3xl font-extrabold text-white leading-tight mb-4">
            Tu operación bajo <span style={{ color: '#00E87A' }}>control total</span>
          </h2>
          <p className="text-base leading-relaxed" style={{ color: '#6B7A8D' }}>
            Inventario, producción, logística con blockchain y cumplimiento EUDR. Todo en una plataforma.
          </p>
        </div>

        <div className="relative z-10 flex gap-8">
          {[
            { n: '6', l: 'Módulos' },
            { n: 'Blockchain', l: 'Verificable' },
            { n: 'EUDR', l: 'Nativo' },
          ].map(s => (
            <div key={s.l}>
              <div className="text-lg font-extrabold text-white">{s.n}</div>
              <div className="text-xs" style={{ color: '#6B7A8D' }}>{s.l}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Right — form */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12" style={{ background: '#0E1318' }}>
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: '#00E87A' }}>
              <span className="text-black font-extrabold text-sm">T</span>
            </div>
            <span className="font-bold text-white text-xl">Trace<span style={{ color: '#00E87A' }}>Log</span></span>
          </div>

          <h1 className="text-2xl font-extrabold text-white mb-2">Iniciar sesión</h1>
          <p className="text-sm mb-8" style={{ color: '#6B7A8D' }}>Ingresa tu email y contraseña para acceder</p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Email</label>
              <input
                {...register('email')}
                type="email"
                autoComplete="email"
                placeholder="tu@email.com"
                className="h-11 w-full rounded-lg border px-4 py-2.5 text-sm text-white placeholder:text-muted-foreground focus:outline-none focus:ring-2"
                style={{ background: '#141A22', borderColor: 'rgba(255,255,255,0.06)', focusRingColor: '#00E87A' }}
              />
              {errors.email && <p className="mt-1.5 text-xs text-red-400">{errors.email.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Contraseña</label>
              <div className="relative">
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="Ingresa tu contraseña"
                  className="h-11 w-full rounded-lg border px-4 py-2.5 pr-11 text-sm text-white placeholder:text-muted-foreground focus:outline-none focus:ring-2"
                  style={{ background: '#141A22', borderColor: 'rgba(255,255,255,0.06)' }}
                />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2">
                  {showPassword ? <Eye className="h-4 w-4 text-muted-foreground" /> : <EyeOff className="h-4 w-4 text-muted-foreground" />}
                </button>
              </div>
              {errors.password && <p className="mt-1.5 text-xs text-red-400">{errors.password.message}</p>}
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" className="h-4 w-4 rounded border-gray-600 text-green-500 focus:ring-green-500 bg-transparent" />
                <span className="text-sm text-muted-foreground">Mantener sesión</span>
              </label>
              <Link to="/forgot-password" className="text-sm font-medium" style={{ color: '#00E87A' }}>¿Olvidaste tu contraseña?</Link>
            </div>

            {login.error && (
              <div className="rounded-lg px-4 py-3 text-sm text-red-300" style={{ background: 'rgba(255,71,87,0.1)', border: '1px solid rgba(255,71,87,0.2)' }}>
                {login.error.message}
              </div>
            )}

            <button
              type="submit"
              disabled={login.isPending}
              className="flex w-full items-center justify-center rounded-lg px-4 py-3 text-sm font-bold text-black transition hover:opacity-90 disabled:opacity-50"
              style={{ background: '#00E87A' }}
            >
              {login.isPending ? 'Iniciando...' : 'Iniciar sesión'}
            </button>
          </form>

          <p className="mt-6 text-sm text-center" style={{ color: '#6B7A8D' }}>
            ¿No tienes cuenta?{' '}
            <Link to="/register" className="font-semibold" style={{ color: '#00E87A' }}>Regístrate</Link>
          </p>

        </div>
      </div>
    </div>
  )
}
