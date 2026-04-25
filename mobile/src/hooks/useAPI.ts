import { useQuery, useMutation, useQueryClient, QueryKey } from '@tanstack/react-query';

export function useAPIQuery<T>(
  queryKey: QueryKey,
  fetcher: () => Promise<T>,
  options?: {
    enabled?: boolean;
    staleTime?: number;
    gcTime?: number;
    retry?: number;
  },
) {
  return useQuery<T>({
    queryKey,
    queryFn: fetcher,
    staleTime: options?.staleTime ?? 5 * 60 * 1000, // 5 min
    gcTime: options?.gcTime ?? 10 * 60 * 1000, // 10 min
    retry: options?.retry ?? 2,
    enabled: options?.enabled !== false,
  });
}

export function useAPIMutation<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  options?: {
    onSuccess?: (data: TData, variables: TVariables) => void;
    onError?: (error: unknown, variables: TVariables) => void;
    invalidateKeys?: QueryKey[];
  },
) {
  const queryClient = useQueryClient();

  return useMutation<TData, unknown, TVariables>({
    mutationFn,
    onSuccess: (data, variables) => {
      options?.onSuccess?.(data, variables);
      if (options?.invalidateKeys) {
        options.invalidateKeys.forEach((key) => {
          queryClient.invalidateQueries({ queryKey: key });
        });
      }
    },
    onError: options?.onError,
  });
}
