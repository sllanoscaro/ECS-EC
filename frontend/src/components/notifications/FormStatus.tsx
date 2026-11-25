/**008 distinct accessible feedback; failures never become an empty successful list. */
export function FormStatus({busy,error,success}:{busy?:boolean;error?:string;success?:string}) {
 return <>{busy&&<p role="status">Guardando configuración…</p>}{error&&<p role="alert" className="notice notice--error">{error}</p>}{success&&<p role="status">{success}</p>}</>;
}
