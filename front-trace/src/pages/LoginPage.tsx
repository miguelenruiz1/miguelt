import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff, ChevronLeft } from 'lucide-react'
import { BlockchainAnimation } from '@/components/auth/BlockchainAnimation'
import { useLogin } from '@/hooks/useAuth'

const schema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'Contraseña requerida'),
})

type FormData = z.infer<typeof schema>

export function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const login = useLogin()

  const onSubmit = (data: FormData) => login.mutate(data)

  return (
    <div className="relative bg-white">
      <div className="relative flex flex-col justify-center w-full min-h-screen lg:h-screen lg:flex-row">
        {/* Left — form */}
        <div className="flex flex-col flex-1 px-5 sm:px-6 lg:px-0">
          <div className="w-full max-w-md pt-8 sm:pt-10 mx-auto">
            <Link
              to="/"
              className="inline-flex items-center text-sm text-gray-500 transition-colors hover:text-gray-700"
            >
              <ChevronLeft className="h-5 w-5" />
              Volver al inicio
            </Link>
          </div>

          <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto pb-8 lg:pb-0">
            <div>
              {/* Logo */}
              <div className="flex items-center gap-2.5 mb-6">
                <svg width="34" height="34" viewBox="0 0 34 34" fill="none" className="shrink-0">
                  <rect width="34" height="34" rx="8" fill="#16a34a" />
                  <path d="M8 11h18v2.5H18.5V25H15V13.5H8V11Z" fill="white" />
                  <path d="M20 17h2.5v5.5H27V25H20V17Z" fill="white" opacity="0.7" />
                </svg>
                <p className="text-[19px] leading-none tracking-tight">
                  <span className="font-bold text-gray-900">Trace</span>
                  <span className="font-medium text-primary">Log</span>
                </p>
              </div>

              <div className="mb-5 sm:mb-8">
                <h1 className="mb-2 text-2xl font-semibold text-gray-800 sm:text-3xl">
                  Iniciar sesión
                </h1>
                <p className="text-sm text-gray-500">
                  Ingresa tu email y contraseña para acceder
                </p>
              </div>

              <div>
                {/* Form */}
                <form onSubmit={handleSubmit(onSubmit)}>
                  <div className="space-y-6">
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-gray-700">
                        Email <span className="text-red-500">*</span>
                      </label>
                      <input
                        {...register('email')}
                        type="email"
                        autoComplete="email"
                        placeholder="tu@email.com"
                        className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-sm placeholder:text-gray-400 focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20"
                      />
                      {errors.email && (
                        <p className="mt-1.5 text-xs text-red-500">{errors.email.message}</p>
                      )}
                    </div>

                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-gray-700">
                        Contraseña <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <input
                          {...register('password')}
                          type={showPassword ? 'text' : 'password'}
                          autoComplete="current-password"
                          placeholder="Ingresa tu contraseña"
                          className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-sm placeholder:text-gray-400 focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20"
                        />
                        <span
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                        >
                          {showPassword ? (
                            <Eye className="h-5 w-5 text-gray-500" />
                          ) : (
                            <EyeOff className="h-5 w-5 text-gray-500" />
                          )}
                        </span>
                      </div>
                      {errors.password && (
                        <p className="mt-1.5 text-xs text-red-500">{errors.password.message}</p>
                      )}
                    </div>

                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input type="checkbox" className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-ring" />
                        <span className="text-sm font-normal text-gray-700">
                          Mantener sesión
                        </span>
                      </label>
                      <Link
                        to="/forgot-password"
                        className="text-sm text-primary hover:text-primary"
                      >
                        ¿Olvidaste tu contraseña?
                      </Link>
                    </div>

                    {login.error && (
                      <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                        {login.error.message}
                      </div>
                    )}

                    <div>
                      <button
                        type="submit"
                        disabled={login.isPending}
                        className="flex w-full items-center justify-center rounded-lg bg-primary px-4 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-primary disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {login.isPending ? 'Iniciando...' : 'Iniciar sesión'}
                      </button>
                    </div>
                  </div>
                </form>

                <div className="mt-5">
                  <p className="text-sm font-normal text-center text-gray-700 sm:text-start">
                    ¿No tienes cuenta?{' '}
                    <Link to="/register" className="text-primary hover:text-primary">
                      Regístrate
                    </Link>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right — branded panel */}
        <div className="relative hidden w-full h-full lg:w-1/2 lg:block overflow-hidden">
          <BlockchainAnimation />
        </div>
      </div>
    </div>
  )
}
