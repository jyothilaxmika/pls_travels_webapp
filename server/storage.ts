import { type User, type InsertUser, type DriverProfile, type InsertDriverProfile, type AuditLog, type InsertAuditLog, type AuditLogWithUser, DriverStatus, users, driverProfiles, auditLogs } from "@shared/schema";
import { db } from "./db";
import { eq, desc } from "drizzle-orm";

// Storage interface with audit logging support
export interface IStorage {
  // User methods
  getUser(id: number): Promise<User | undefined>;
  getUserByPhone(phoneNumber: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  upsertUser(phoneNumber: string, userData: Partial<InsertUser>): Promise<User>;
  // Driver profile methods
  getDriverProfile(userId: number): Promise<DriverProfile | undefined>;
  upsertDriverProfile(input: InsertDriverProfile): Promise<DriverProfile>;
  setDriverStatus(userId: number, status: DriverStatus): Promise<DriverProfile | undefined>;
  listDriversByStatus(status?: DriverStatus): Promise<DriverProfile[]>;
  // Audit log methods
  createAuditLog(auditLog: InsertAuditLog): Promise<AuditLog>;
  getAuditLogs(limit?: number): Promise<AuditLogWithUser[]>;
}

// Database implementation based on javascript_database blueprint
export class DatabaseStorage implements IStorage {
  // User methods
  async getUser(id: number): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user || undefined;
  }

  async getUserByPhone(phoneNumber: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.phoneNumber, phoneNumber));
    return user || undefined;
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const [user] = await db.insert(users).values(insertUser).returning();
    return user;
  }

  async upsertUser(phoneNumber: string, userData: Partial<InsertUser>): Promise<User> {
    const existingUser = await this.getUserByPhone(phoneNumber);
    
    if (existingUser) {
      // Update existing user
      const [updatedUser] = await db
        .update(users)
        .set({ ...userData, phoneNumber })
        .where(eq(users.phoneNumber, phoneNumber))
        .returning();
      return updatedUser;
    } else {
      // Create new user
      const [newUser] = await db
        .insert(users)
        .values({ phoneNumber, ...userData })
        .returning();
      return newUser;
    }
  }

  // Driver profile methods
  async getDriverProfile(userId: number): Promise<DriverProfile | undefined> {
    const [profile] = await db.select().from(driverProfiles).where(eq(driverProfiles.userId, userId));
    return profile || undefined;
  }

  async upsertDriverProfile(input: InsertDriverProfile): Promise<DriverProfile> {
    const existingProfile = await this.getDriverProfile(input.userId);
    
    if (existingProfile) {
      // Update existing profile
      const [updatedProfile] = await db
        .update(driverProfiles)
        .set({ ...input, updatedAt: new Date() })
        .where(eq(driverProfiles.userId, input.userId))
        .returning();
      return updatedProfile;
    } else {
      // Create new profile
      const [newProfile] = await db
        .insert(driverProfiles)
        .values(input)
        .returning();
      return newProfile;
    }
  }

  async setDriverStatus(userId: number, status: DriverStatus): Promise<DriverProfile | undefined> {
    const [updatedProfile] = await db
      .update(driverProfiles)
      .set({ status, updatedAt: new Date() })
      .where(eq(driverProfiles.userId, userId))
      .returning();
    
    return updatedProfile || undefined;
  }

  async listDriversByStatus(status?: DriverStatus): Promise<DriverProfile[]> {
    if (status) {
      return await db.select().from(driverProfiles).where(eq(driverProfiles.status, status));
    }
    return await db.select().from(driverProfiles);
  }

  // Audit log methods  
  async createAuditLog(auditLog: InsertAuditLog): Promise<AuditLog> {
    const [log] = await db.insert(auditLogs).values(auditLog).returning();
    return log;
  }

  async getAuditLogs(limit: number = 100): Promise<AuditLogWithUser[]> {
    return await db
      .select({
        id: auditLogs.id,
        userId: auditLogs.userId,
        action: auditLogs.action,
        targetType: auditLogs.targetType,
        targetId: auditLogs.targetId,
        details: auditLogs.details,
        ipAddress: auditLogs.ipAddress,
        userAgent: auditLogs.userAgent,
        createdAt: auditLogs.createdAt,
        userFullName: users.fullName
      })
      .from(auditLogs)
      .leftJoin(users, eq(auditLogs.userId, users.id))
      .orderBy(desc(auditLogs.createdAt))
      .limit(limit);
  }
}

export const storage = new DatabaseStorage();
