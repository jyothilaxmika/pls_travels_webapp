import { z } from "zod";
import { pgTable, varchar, timestamp, text, pgEnum, serial, boolean } from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";

// Driver onboarding enums and types
export enum DriverStatus {
  PENDING = 'pending',
  APPROVED = 'approved', 
  REJECTED = 'rejected'
}

// Database enums
export const driverStatusEnum = pgEnum('driver_status', ['pending', 'approved', 'rejected']);
export const userRoleEnum = pgEnum('user_role', ['driver', 'admin', 'customer', 'manager']);
export const auditActionEnum = pgEnum('audit_action', [
  'driver_approved', 
  'driver_rejected', 
  'driver_profile_created',
  'user_login',
  'user_created',
  'role_changed'
]);

// Database Tables
export const users = pgTable('users', {
  id: serial("id").primaryKey(),
  phoneNumber: varchar("phone_number", { length: 20 }).unique().notNull(),
  username: varchar("username", { length: 50 }),
  fullName: varchar("full_name", { length: 100 }),
  email: varchar("email", { length: 255 }),
  role: userRoleEnum("role").default('customer').notNull(),
  isVerified: boolean("is_verified").default(false).notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const driverProfiles = pgTable('driver_profiles', {
  id: serial("id").primaryKey(),
  userId: serial("user_id").references(() => users.id).notNull(),
  fullName: varchar("full_name", { length: 100 }).notNull(),
  phone: varchar("phone", { length: 20 }).notNull(),
  address: text("address"),
  aadharNumber: varchar("aadhar_number", { length: 12 }).notNull(),
  licenseNumber: varchar("license_number", { length: 50 }).notNull(),
  bankName: varchar("bank_name", { length: 100 }),
  accountNumber: varchar("account_number", { length: 50 }),
  ifscCode: varchar("ifsc_code", { length: 15 }),
  accountHolderName: varchar("account_holder_name", { length: 100 }),
  branchId: varchar("branch_id", { length: 50 }),
  status: driverStatusEnum("status").default('pending').notNull(),
  // Document file paths
  aadharFrontPath: varchar("aadhar_front_path", { length: 255 }),
  aadharBackPath: varchar("aadhar_back_path", { length: 255 }),
  licenseFrontPath: varchar("license_front_path", { length: 255 }),
  licenseBackPath: varchar("license_back_path", { length: 255 }),
  profilePhotoPath: varchar("profile_photo_path", { length: 255 }),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export const auditLogs = pgTable('audit_logs', {
  id: serial("id").primaryKey(),
  userId: serial("user_id").references(() => users.id).notNull(),
  action: auditActionEnum("action").notNull(),
  targetType: varchar("target_type", { length: 50 }), // 'driver', 'user', etc.
  targetId: varchar("target_id", { length: 50 }), // ID of the affected resource
  details: text("details"), // JSON string with action details
  ipAddress: varchar("ip_address", { length: 45 }),
  userAgent: text("user_agent"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Relations
export const usersRelations = relations(users, ({ one, many }) => ({
  driverProfile: one(driverProfiles, {
    fields: [users.id],
    references: [driverProfiles.userId],
  }),
  auditLogs: many(auditLogs),
}));

export const driverProfilesRelations = relations(driverProfiles, ({ one }) => ({
  user: one(users, {
    fields: [driverProfiles.userId],
    references: [users.id],
  }),
}));

export const auditLogsRelations = relations(auditLogs, ({ one }) => ({
  user: one(users, {
    fields: [auditLogs.userId],
    references: [users.id],
  }),
}));

// Zod schemas from Drizzle tables
export const insertUserSchema = createInsertSchema(users);
export const selectUserSchema = createSelectSchema(users);
export const insertDriverProfileSchema = createInsertSchema(driverProfiles);
export const selectDriverProfileSchema = createSelectSchema(driverProfiles);
export const insertAuditLogSchema = createInsertSchema(auditLogs);
export const selectAuditLogSchema = createSelectSchema(auditLogs);

// Types
export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;
export type DriverProfile = typeof driverProfiles.$inferSelect;
export type InsertDriverProfile = typeof driverProfiles.$inferInsert;
export type AuditLog = typeof auditLogs.$inferSelect;
export type InsertAuditLog = typeof auditLogs.$inferInsert;

// OTP schema (remains in-memory for now)
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
