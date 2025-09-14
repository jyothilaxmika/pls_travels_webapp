import { type User, type InsertUser, type DriverProfile, type InsertDriverProfile, DriverStatus } from "@shared/schema";
import { randomUUID } from "crypto";

// modify the interface with any CRUD methods
// you might need

export interface IStorage {
  getUser(id: string): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  // Driver profile methods
  getDriverProfile(userId: string): Promise<DriverProfile | undefined>;
  upsertDriverProfile(input: InsertDriverProfile): Promise<DriverProfile>;
  setDriverStatus(userId: string, status: DriverStatus): Promise<DriverProfile | undefined>;
  listDriversByStatus(status?: DriverStatus): Promise<DriverProfile[]>;
}

export class MemStorage implements IStorage {
  private users: Map<string, User>;
  private driverProfiles: Map<string, DriverProfile>; // keyed by userId

  constructor() {
    this.users = new Map();
    this.driverProfiles = new Map();
  }

  async getUser(id: string): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.username === username,
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = randomUUID();
    const user: User = { ...insertUser, id };
    this.users.set(id, user);
    return user;
  }

  async getDriverProfile(userId: string): Promise<DriverProfile | undefined> {
    return this.driverProfiles.get(userId);
  }

  async upsertDriverProfile(input: InsertDriverProfile): Promise<DriverProfile> {
    const id = randomUUID();
    const now = new Date();
    const existingProfile = this.driverProfiles.get(input.userId);
    
    const profile: DriverProfile = {
      id: existingProfile?.id || id,
      ...input,
      createdAt: existingProfile?.createdAt || now,
      updatedAt: now,
    };
    
    this.driverProfiles.set(input.userId, profile);
    return profile;
  }

  async setDriverStatus(userId: string, status: DriverStatus): Promise<DriverProfile | undefined> {
    const profile = this.driverProfiles.get(userId);
    if (!profile) return undefined;
    
    profile.status = status;
    profile.updatedAt = new Date();
    this.driverProfiles.set(userId, profile);
    return profile;
  }

  async listDriversByStatus(status?: DriverStatus): Promise<DriverProfile[]> {
    const profiles = Array.from(this.driverProfiles.values());
    if (status) {
      return profiles.filter(p => p.status === status);
    }
    return profiles;
  }
}

export const storage = new MemStorage();
