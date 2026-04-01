import { Link } from 'react-router-dom'

function GridShape() {
  return (
    <>
      <div className="absolute right-0 top-0 -z-[1] w-full max-w-[250px] xl:max-w-[450px]">
        <svg viewBox="0 0 405 405" fill="none" xmlns="http://www.w3.org/2000/svg">
          <g opacity="0.5">
            {Array.from({ length: 15 }, (_, r) =>
              Array.from({ length: 15 }, (_, c) => (
                <rect key={`${r}-${c}`} x={c * 27} y={r * 27} width="3.78" height="3.78" rx="1.89" fill="#D0D5DD" />
              ))
            ).flat()}
          </g>
        </svg>
      </div>
      <div className="absolute bottom-0 left-0 -z-[1] w-full max-w-[250px] rotate-180 xl:max-w-[450px]">
        <svg viewBox="0 0 405 405" fill="none" xmlns="http://www.w3.org/2000/svg">
          <g opacity="0.5">
            {Array.from({ length: 15 }, (_, r) =>
              Array.from({ length: 15 }, (_, c) => (
                <rect key={`${r}-${c}`} x={c * 27} y={r * 27} width="3.78" height="3.78" rx="1.89" fill="#D0D5DD" />
              ))
            ).flat()}
          </g>
        </svg>
      </div>
    </>
  )
}

function Illustration404() {
  return (
    <svg className="w-full max-w-[472px] h-auto" viewBox="0 0 472 158" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Center "0" — rounded rectangle */}
      <rect x="203.103" y="41.7015" width="22.1453" height="20.7141" rx="2.63433" fill="#465FFF" stroke="#465FFF" strokeWidth="0.752667" />
      <rect x="246.752" y="41.7015" width="22.1453" height="20.7141" rx="2.63433" fill="#465FFF" stroke="#465FFF" strokeWidth="0.752667" />
      <rect x="258.201" y="98.2303" width="22.1453" height="20.7141" rx="2.63433" fill="#465FFF" stroke="#465FFF" strokeWidth="0.752667" />
      <rect x="191.654" y="98.2303" width="22.1453" height="20.7141" rx="2.63433" fill="#465FFF" stroke="#465FFF" strokeWidth="0.752667" />
      <rect x="207.396" y="82.847" width="57.5655" height="20.7141" rx="2.63433" fill="#465FFF" stroke="#465FFF" strokeWidth="0.752667" />
      <rect x="152.769" y="15.167" width="166.462" height="130.311" rx="28" stroke="#465FFF" strokeWidth="24" />

      {/* Left "4" */}
      <rect x="0.0405273" y="0.522461" width="32.6255" height="77.5957" rx="6.26271" fill="#465FFF" />
      <rect x="0.0405273" y="0.522461" width="32.6255" height="77.5957" rx="6.26271" stroke="#465FFF" />
      <rect x="75.8726" y="3.16748" width="32.6255" height="154.31" rx="6.26271" fill="#465FFF" />
      <rect x="75.8726" y="3.16748" width="32.6255" height="154.31" rx="6.26271" stroke="#465FFF" />
      <rect x="16.7939" y="91.3442" width="32.6255" height="77.5957" rx="6.26271" transform="rotate(-90 16.7939 91.3442)" fill="#465FFF" />
      <rect x="16.7939" y="91.3442" width="32.6255" height="77.5957" rx="6.26271" transform="rotate(-90 16.7939 91.3442)" stroke="#465FFF" />

      {/* Right "4" */}
      <rect x="363.502" y="0.522461" width="32.6255" height="77.5957" rx="6.26271" fill="#465FFF" />
      <rect x="363.502" y="0.522461" width="32.6255" height="77.5957" rx="6.26271" stroke="#465FFF" />
      <rect x="439.334" y="3.16748" width="32.6255" height="154.31" rx="6.26271" fill="#465FFF" />
      <rect x="439.334" y="3.16748" width="32.6255" height="154.31" rx="6.26271" stroke="#465FFF" />
      <rect x="380.255" y="91.3442" width="32.6255" height="77.5957" rx="6.26271" transform="rotate(-90 380.255 91.3442)" fill="#465FFF" />
      <rect x="380.255" y="91.3442" width="32.6255" height="77.5957" rx="6.26271" transform="rotate(-90 380.255 91.3442)" stroke="#465FFF" />
    </svg>
  )
}

export function NotFoundPage() {
  return (
    <div className="relative flex flex-col items-center justify-center min-h-screen px-4 py-8 sm:p-6 overflow-hidden bg-card z-[1]">
      <GridShape />

      <div className="mx-auto w-full max-w-[242px] text-center sm:max-w-[472px]">
        <h1 className="mb-8 font-bold text-foreground text-2xl xl:text-4xl">
          ERROR
        </h1>

        <Illustration404 />

        <p className="mt-10 mb-6 text-base text-foreground sm:text-lg">
          No pudimos encontrar la página que buscas
        </p>

        <Link
          to="/"
          className="inline-flex items-center justify-center rounded-lg border border-gray-300 bg-card px-5 py-3.5 text-sm font-medium text-foreground  hover:bg-muted hover:text-foreground transition-colors"
        >
          Volver al inicio
        </Link>
      </div>

      <p className="absolute text-sm text-center text-muted-foreground -translate-x-1/2 bottom-6 left-1/2">
        &copy; {new Date().getFullYear()} — TraceLog
      </p>
    </div>
  )
}
