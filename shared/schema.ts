import { z } from "zod";

// User schema for authentication
export const userSchema = z.object({
  id: z.string(),
  phoneNumber: z.string(),
  fullName: z.string().optional(),
  email: z.string().email().optional(),
  role: z.enum(['driver', 'admin', 'customer']).default('customer'),
  isVerified: z.boolean().default(false),
  createdAt: z.date().default(() => new Date()),
});

export type User = z.infer<typeof userSchema>;

// OTP schema
export const otpSchema = z.object({
  id: z.string(),
  phoneNumber: z.string(),
  code: z.string().length(6),
  expiresAt: z.date(),
  attempts: z.number().default(0),
  verified: z.boolean().default(false),
  createdAt: z.date().default(() => new Date()),
});

export type OTP = z.infer<typeof otpSchema>;

// Authentication request schemas
export const sendOTPSchema = z.object({
  phoneNumber: z.string().regex(/^\+?[1-9]\d{1,14}$/, "Invalid phone number format"),
  type: z.enum(['login', 'signup']),
  fullName: z.string().optional(),
  email: z.string().email().optional(),
});

export const verifyOTPSchema = z.object({
  phoneNumber: z.string(),
  code: z.string().length(6, "OTP must be 6 digits"),
  type: z.enum(['login', 'signup']),
});

export const resendOTPSchema = z.object({
  phoneNumber: z.string(),
});

export type SendOTPRequest = z.infer<typeof sendOTPSchema>;
export type VerifyOTPRequest = z.infer<typeof verifyOTPSchema>;
export type ResendOTPRequest = z.infer<typeof resendOTPSchema>;
