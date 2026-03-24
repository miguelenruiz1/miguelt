import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff, Check, X, ChevronLeft } from 'lucide-react'
import { BlockchainAnimation } from '@/components/auth/BlockchainAnimation'
import { useRegister } from '@/hooks/useAuth'

const schema = z
  .object({
    full_name: z.string().min(1, 'Nombre requerido').max(255),
    username: z
      .string()
      .min(3, 'Mínimo 3 caracteres')
      .max(100)
      .regex(/^[a-zA-Z0-9._-]+$/, 'Solo letras, números, puntos, guiones'),
    email: z.string().email('Email inválido'),
    phone: z.string().max(30).optional().or(z.literal('')),
    company: z.string().max(255).optional().or(z.literal('')),
    job_title: z.string().max(255).optional().or(z.literal('')),
    password: z.string().min(8, 'Mínimo 8 caracteres'),
    confirmPassword: z.string().min(1, 'Confirma tu contraseña'),
    terms: z.literal(true, { errorMap: () => ({ message: 'Debes aceptar los términos' }) }),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: 'Las contraseñas no coinciden',
    path: ['confirmPassword'],
  })

type FormData = z.infer<typeof schema>

function getPasswordStrength(pw: string): { score: number; label: string; color: string } {
  let score = 0
  if (pw.length >= 8) score++
  if (pw.length >= 12) score++
  if (/[A-Z]/.test(pw)) score++
  if (/[0-9]/.test(pw)) score++
  if (/[^A-Za-z0-9]/.test(pw)) score++

  if (score <= 1) return { score, label: 'Débil', color: 'bg-red-500' }
  if (score <= 2) return { score, label: 'Regular', color: 'bg-orange-500' }
  if (score <= 3) return { score, label: 'Buena', color: 'bg-yellow-500' }
  if (score <= 4) return { score, label: 'Fuerte', color: 'bg-green-500' }
  return { score, label: 'Muy fuerte', color: 'bg-emerald-500' }
}

const PasswordRule = ({ ok, text }: { ok: boolean; text: string }) => (
  <span className={`flex items-center gap-1 text-xs ${ok ? 'text-green-600' : 'text-gray-400'}`}>
    {ok ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
    {text}
  </span>
)

const inputClass =
  'h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-sm placeholder:text-gray-400 focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20'

export function RegisterPage() {
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [step, setStep] = useState<1 | 2>(1)

  const {
    register,
    handleSubmit,
    watch,
    trigger,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    mode: 'onChange',
    defaultValues: { terms: false as any },
  })

  const registerMutation = useRegister()
  const password = watch('password') || ''
  const strength = getPasswordStrength(password)

  const onSubmit = (data: FormData) => {
    registerMutation.mutate({
      email: data.email,
      username: data.username,
      full_name: data.full_name,
      password: data.password,
      phone: data.phone || undefined,
      company: data.company || undefined,
      job_title: data.job_title || undefined,
    })
  }

  const goToStep2 = async () => {
    const valid = await trigger(['full_name', 'username', 'email', 'phone', 'company', 'job_title'])
    if (valid) setStep(2)
  }

  return (
    <div className="relative bg-white">
      <div className="relative flex flex-col justify-center w-full min-h-screen lg:h-screen lg:flex-row">
        {/* Left — form */}
        <div className="flex flex-col flex-1 w-full overflow-y-auto lg:w-1/2 no-scrollbar px-5 sm:px-6 lg:px-0">
          <div className="w-full max-w-md mx-auto mb-5 pt-6 sm:pt-10">
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
                  Crear cuenta
                </h1>
                <p className="text-sm text-gray-500">
                  Completa tus datos para registrarte
                </p>
              </div>

              <div>
                {/* Step indicator */}
                <div className="flex items-center gap-3 mb-5">
                  <div className={`flex items-center gap-1.5 text-xs font-medium ${step === 1 ? 'text-primary' : 'text-gray-400'}`}>
                    <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${step === 1 ? 'bg-primary text-white' : 'bg-gray-100 text-gray-500'}`}>1</span>
                    Información
                  </div>
                  <div className="w-10 h-px bg-gray-200" />
                  <div className={`flex items-center gap-1.5 text-xs font-medium ${step === 2 ? 'text-primary' : 'text-gray-400'}`}>
                    <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${step === 2 ? 'bg-primary text-white' : 'bg-gray-100 text-gray-500'}`}>2</span>
                    Seguridad
                  </div>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit(onSubmit)}>
                  <div className="space-y-5">
                    {step === 1 && (
                      <>
                        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                          <div className="sm:col-span-1">
                            <label className="mb-1.5 block text-sm font-medium text-gray-700">
                              Nombre completo <span className="text-red-500">*</span>
                            </label>
                            <input {...register('full_name')} className={inputClass} placeholder="Juan García López" />
                            {errors.full_name && <p className="mt-1.5 text-xs text-red-500">{errors.full_name.message}</p>}
                          </div>
                          <div className="sm:col-span-1">
                            <label className="mb-1.5 block text-sm font-medium text-gray-700">
                              Usuario <span className="text-red-500">*</span>
                            </label>
                            <input {...register('username')} className={inputClass} placeholder="juan.garcia" />
                            {errors.username && <p className="mt-1.5 text-xs text-red-500">{errors.username.message}</p>}
                          </div>
                        </div>

                        <div>
                          <label className="mb-1.5 block text-sm font-medium text-gray-700">
                            Email <span className="text-red-500">*</span>
                          </label>
                          <input {...register('email')} type="email" autoComplete="email" className={inputClass} placeholder="juan@empresa.com" />
                          {errors.email && <p className="mt-1.5 text-xs text-red-500">{errors.email.message}</p>}
                        </div>

                        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                          <div className="sm:col-span-1">
                            <label className="mb-1.5 block text-sm font-medium text-gray-700">Teléfono</label>
                            <input {...register('phone')} type="tel" className={inputClass} placeholder="+57 300 123 4567" />
                            {errors.phone && <p className="mt-1.5 text-xs text-red-500">{errors.phone.message}</p>}
                          </div>
                          <div className="sm:col-span-1">
                            <label className="mb-1.5 block text-sm font-medium text-gray-700">Empresa</label>
                            <input {...register('company')} className={inputClass} placeholder="Mi Empresa S.A.S" />
                          </div>
                        </div>

                        <div>
                          <label className="mb-1.5 block text-sm font-medium text-gray-700">Cargo</label>
                          <input {...register('job_title')} className={inputClass} placeholder="Gerente de logística" />
                        </div>

                        <div>
                          <button
                            type="button"
                            onClick={goToStep2}
                            className="flex w-full items-center justify-center rounded-lg bg-primary px-4 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-primary"
                          >
                            Continuar
                          </button>
                        </div>
                      </>
                    )}

                    {step === 2 && (
                      <>
                        <div>
                          <label className="mb-1.5 block text-sm font-medium text-gray-700">
                            Contraseña <span className="text-red-500">*</span>
                          </label>
                          <div className="relative">
                            <input
                              {...register('password')}
                              type={showPassword ? 'text' : 'password'}
                              autoComplete="new-password"
                              className={inputClass}
                              placeholder="Mínimo 8 caracteres"
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
                          {errors.password && <p className="mt-1.5 text-xs text-red-500">{errors.password.message}</p>}

                          {password.length > 0 && (
                            <div className="mt-2.5 space-y-1.5">
                              <div className="flex gap-1">
                                {[1, 2, 3, 4, 5].map((i) => (
                                  <div
                                    key={i}
                                    className={`h-1.5 flex-1 rounded-full transition-colors ${
                                      i <= strength.score ? strength.color : 'bg-gray-200'
                                    }`}
                                  />
                                ))}
                              </div>
                              <p className={`text-xs font-medium ${strength.color.replace('bg-', 'text-')}`}>
                                {strength.label}
                              </p>
                              <div className="flex flex-wrap gap-x-4 gap-y-0.5">
                                <PasswordRule ok={password.length >= 8} text="8+ caracteres" />
                                <PasswordRule ok={/[A-Z]/.test(password)} text="Mayúscula" />
                                <PasswordRule ok={/[0-9]/.test(password)} text="Número" />
                                <PasswordRule ok={/[^A-Za-z0-9]/.test(password)} text="Especial" />
                              </div>
                            </div>
                          )}
                        </div>

                        <div>
                          <label className="mb-1.5 block text-sm font-medium text-gray-700">
                            Confirmar contraseña <span className="text-red-500">*</span>
                          </label>
                          <div className="relative">
                            <input
                              {...register('confirmPassword')}
                              type={showConfirm ? 'text' : 'password'}
                              autoComplete="new-password"
                              className={inputClass}
                              placeholder="Repite tu contraseña"
                            />
                            <span
                              onClick={() => setShowConfirm(!showConfirm)}
                              className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                            >
                              {showConfirm ? (
                                <Eye className="h-5 w-5 text-gray-500" />
                              ) : (
                                <EyeOff className="h-5 w-5 text-gray-500" />
                              )}
                            </span>
                          </div>
                          {errors.confirmPassword && (
                            <p className="mt-1.5 text-xs text-red-500">{errors.confirmPassword.message}</p>
                          )}
                        </div>

                        <div className="flex items-start gap-3">
                          <input
                            type="checkbox"
                            {...register('terms')}
                            className="mt-0.5 h-5 w-5 rounded border-gray-300 text-primary focus:ring-ring"
                          />
                          <p className="font-normal text-gray-500 text-sm">
                            Al crear una cuenta aceptas los{' '}
                            <span className="text-gray-800">Términos y Condiciones</span>
                            {' '}y nuestra{' '}
                            <span className="text-gray-800">Política de Privacidad</span>
                          </p>
                        </div>
                        {errors.terms && <p className="text-xs text-red-500">{errors.terms.message}</p>}

                        {registerMutation.error && (
                          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                            {registerMutation.error.message}
                          </div>
                        )}

                        {registerMutation.isSuccess && (
                          <div className="rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700">
                            Cuenta creada. Redirigiendo al login...
                          </div>
                        )}

                        <div className="grid grid-cols-2 gap-3">
                          <button
                            type="button"
                            onClick={() => setStep(1)}
                            className="flex items-center justify-center rounded-lg border border-gray-300 px-4 py-3 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                          >
                            Atrás
                          </button>
                          <button
                            type="submit"
                            disabled={registerMutation.isPending}
                            className="flex items-center justify-center rounded-lg bg-primary px-4 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-primary disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {registerMutation.isPending ? 'Creando...' : 'Crear cuenta'}
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </form>

                <div className="mt-5">
                  <p className="text-sm font-normal text-center text-gray-700 sm:text-start">
                    ¿Ya tienes cuenta?{' '}
                    <Link to="/login" className="text-primary hover:text-primary">
                      Iniciar sesión
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
