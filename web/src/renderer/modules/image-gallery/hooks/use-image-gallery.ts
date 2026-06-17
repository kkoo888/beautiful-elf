/** 图片画廊 React Query Hooks */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchImages, fetchImageTags, fetchImageById,
  createImage, updateImage, deleteImage, generateImage, generateImageImg2Img,
} from '../services/image-gallery-api'
import type {
  ImageGalleryFormInput, ImageGalleryUpdateInput, ImageGenerateInput, ImageImg2ImgInput,
} from '../types'

const KEY = ['image-gallery']

export function useImageGallery() {
  const queryClient = useQueryClient()

  const imagesQuery = (params?: { tag?: string; enabled?: number; page?: number; pageSize?: number }) =>
    useQuery({
      queryKey: [...KEY, 'list', params],
      queryFn: () => fetchImages(params),
    })

  const tagsQuery = () =>
    useQuery({
      queryKey: [...KEY, 'tags'],
      queryFn: () => fetchImageTags(),
    })

  const imageQuery = (id: number) =>
    useQuery({
      queryKey: [...KEY, 'detail', id],
      queryFn: () => fetchImageById(id),
      enabled: id > 0,
    })

  const createMut = useMutation({
    mutationFn: (input: ImageGalleryFormInput) => createImage(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY })
    },
  })

  const updateMut = useMutation({
    mutationFn: ({ id, input }: { id: number; input: ImageGalleryUpdateInput }) => updateImage(id, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY })
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteImage(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY })
    },
  })

  const generateMut = useMutation({
    mutationFn: (input: ImageGenerateInput) => generateImage(input),
  })

  const generateImg2ImgMut = useMutation({
    mutationFn: (input: ImageImg2ImgInput) => generateImageImg2Img(input),
  })

  return {
    imagesQuery,
    tagsQuery,
    imageQuery,
    createImage: (input: ImageGalleryFormInput) => createMut.mutateAsync(input),
    updateImage: (id: number, input: ImageGalleryUpdateInput) => updateMut.mutateAsync({ id, input }),
    deleteImage: (id: number) => deleteMut.mutateAsync(id),
    generateImage: (input: ImageGenerateInput) => generateMut.mutateAsync(input),
    generateImageImg2Img: (input: ImageImg2ImgInput) => generateImg2ImgMut.mutateAsync(input),
    isCreating: createMut.isPending,
    isUpdating: updateMut.isPending,
    isDeleting: deleteMut.isPending,
    isGenerating: generateMut.isPending,
    isImg2Imging: generateImg2ImgMut.isPending,
  }
}
