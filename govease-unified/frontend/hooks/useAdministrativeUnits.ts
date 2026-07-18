import useSWR from "swr";
import { getDistricts, getProvinces, getWards } from "../lib/api";
import type { AdministrativeUnit, Province } from "../lib/types";

export function useProvinces() {
  const { data, error, isLoading } = useSWR<{ items: Province[]; total: number; source_url: string }>(
    "/api/v1/administrative-units/provinces",
    getProvinces
  );

  return {
    provinces: data?.items || [],
    isLoading,
    error,
    sourceUrl: data?.source_url,
  };
}

export function useDistricts(provinceCode: string) {
  const { data, error, isLoading } = useSWR<{ items: AdministrativeUnit[]; total: number; source_url: string }>(
    provinceCode ? `/api/v1/administrative-units/districts?province_code=${provinceCode}` : null,
    () => getDistricts(provinceCode)
  );

  return {
    districts: data?.items || [],
    isLoading,
    error,
    sourceUrl: data?.source_url,
  };
}

export function useWards(provinceCode: string, districtCode: string) {
  const { data, error, isLoading } = useSWR<{ items: AdministrativeUnit[]; total: number; source_url: string }>(
    provinceCode && districtCode 
      ? `/api/v1/administrative-units/wards?province_code=${provinceCode}&district_code=${districtCode}` 
      : null,
    () => getWards(provinceCode, districtCode)
  );

  return {
    wards: data?.items || [],
    isLoading,
    error,
    sourceUrl: data?.source_url,
  };
}
