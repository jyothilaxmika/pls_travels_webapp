import { z } from "zod";

// Driver onboarding enums and types
export enum DriverStatus {
  PENDING = 'pending',
  APPROVED = 'approved', 
  REJECTED = 'rejected'
}

// Driver profile schema
export const driverProfileSchema = z.object({
  id: z.string(),
  userId: z.string(),
  fullName: z.string().min(1, "Full name is required"),
  phone: z.string().min(10, "Valid phone number required"),
  address: z.string().optional(),
  aadharNumber: z.string().min(12, "Valid Aadhar number required"),
  licenseNumber: z.string().min(1, "License number is required"),
  bankName: z.string().optional(),
  accountNumber: z.string().optional(),
  ifscCode: z.string().optional(),
  accountHolderName: z.string().optional(),
  branchId: z.string().optional(),
  status: z.nativeEnum(DriverStatus).default(DriverStatus.PENDING),
  // Document file paths
  aadharFrontPath: z.string().optional(),
  aadharBackPath: z.string().optional(),
  licenseFrontPath: z.string().optional(),
  licenseBackPath: z.string().optional(),
  profilePhotoPath: z.string().optional(),
  createdAt: z.date().default(() => new Date()),
  updatedAt: z.date().default(() => new Date())
});

export const insertDriverProfileSchema = driverProfileSchema.omit({ 
  id: true, 
  createdAt: true, 
  updatedAt: true 
});

export type DriverProfile = z.infer<typeof driverProfileSchema>;
export type InsertDriverProfile = z.infer<typeof insertDriverProfileSchema>;

// User schema for authentication
export const userSchema = z.object({
  id: z.string(),
  phoneNumber: z.string(),
  username: z.string().optional(),
  fullName: z.string().optional(),
  email: z.string().email().optional(),
  role: z.enum(['driver', 'admin', 'customer']).default('customer'),
  isVerified: z.boolean().default(false),
  createdAt: z.date().default(() => new Date()),
});

export const insertUserSchema = userSchema.omit({ id: true, createdAt: true });

export type User = z.infer<typeof userSchema>;
export type InsertUser = z.infer<typeof insertUserSchema>;

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
