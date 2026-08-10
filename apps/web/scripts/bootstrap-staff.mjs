import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  createClient,
} from "@supabase/supabase-js";


const __filename =
  fileURLToPath(import.meta.url);

const __dirname =
  path.dirname(__filename);

const repoRoot =
  path.resolve(
    __dirname,
    "../../..",
  );


function readEnvFile(filePath) {
  if (!fs.existsSync(filePath)) {
    return {};
  }

  const result = {};

  const content =
    fs.readFileSync(
      filePath,
      "utf8",
    );

  for (
    const rawLine
    of content.split(/\r?\n/)
  ) {
    const line =
      rawLine.trim();

    if (
      !line ||
      line.startsWith("#")
    ) {
      continue;
    }

    const separatorIndex =
      line.indexOf("=");

    if (separatorIndex < 1) {
      continue;
    }

    const key =
      line
        .slice(
          0,
          separatorIndex,
        )
        .trim();

    let value =
      line
        .slice(
          separatorIndex + 1,
        )
        .trim();

    if (
      (
        value.startsWith('"') &&
        value.endsWith('"')
      )
      ||
      (
        value.startsWith("'") &&
        value.endsWith("'")
      )
    ) {
      value =
        value.slice(1, -1);
    }

    result[key] = value;
  }

  return result;
}


const fileEnv =
  readEnvFile(
    path.join(
      repoRoot,
      ".env",
    ),
  );

const env = {
  ...fileEnv,
  ...process.env,
};


const supabaseUrl =
  env.SUPABASE_LOCAL_URL
  ?? "http://127.0.0.1:55321";

const serviceRoleKey =
  env.SUPABASE_SERVICE_ROLE_KEY;


if (!serviceRoleKey) {
  throw new Error(
    "SUPABASE_SERVICE_ROLE_KEY is required in the root .env file.",
  );
}


const staff = [
  {
    role: "SUPPORT_AGENT",
    name: "Northstar Demo Agent",
    email:
      env.SUPPORT_AGENT_EMAIL
      ?? "agent@northstar.demo",
    password:
      env.SUPPORT_AGENT_PASSWORD,
  },
  {
    role: "SUPPORT_MANAGER",
    name: "Northstar Demo Manager",
    email:
      env.SUPPORT_MANAGER_EMAIL
      ?? "manager@northstar.demo",
    password:
      env.SUPPORT_MANAGER_PASSWORD,
  },
  {
    role: "SYSTEM_ADMIN",
    name: "Northstar Demo Administrator",
    email:
      env.SYSTEM_ADMIN_EMAIL
      ?? "admin@northstar.demo",
    password:
      env.SYSTEM_ADMIN_PASSWORD,
  },
];


for (const member of staff) {
  if (
    !member.password ||
    member.password.length < 12 ||
    member.password.startsWith(
      "replace-with",
    )
  ) {
    throw new Error(
      `A local password of at least 12 characters is required for ${member.email}.`,
    );
  }
}


const supabase =
  createClient(
    supabaseUrl,
    serviceRoleKey,
    {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
        detectSessionInUrl: false,
      },
    },
  );


async function getExistingUsers() {
  const {
    data,
    error,
  } =
    await supabase.auth.admin.listUsers({
      page: 1,
      perPage: 1000,
    });

  if (error) {
    throw error;
  }

  return data.users;
}


async function ensureAuthUser(
  member,
  existingUsers,
) {
  const existing =
    existingUsers.find(
      (user) =>
        user.email?.toLowerCase()
        === member.email.toLowerCase(),
    );

  if (existing) {
    const {
      data,
      error,
    } =
      await supabase.auth.admin.updateUserById(
        existing.id,
        {
          password:
            member.password,

          user_metadata: {
            name:
              member.name,
          },
        },
      );

    if (error) {
      throw error;
    }

    return data.user;
  }


  const {
    data,
    error,
  } =
    await supabase.auth.admin.createUser({
      email:
        member.email,

      password:
        member.password,

      email_confirm: true,

      user_metadata: {
        name:
          member.name,
      },
    });


  if (error) {
    throw error;
  }

  return data.user;
}


async function ensureProfile(
  member,
  user,
) {
  const {
    error,
  } =
    await supabase
      .from("users")
      .upsert(
        {
          id:
            user.id,

          role:
            member.role,

          name:
            member.name,

          email:
            member.email,

          status:
            "ACTIVE",
        },
        {
          onConflict:
            "id",
        },
      );


  if (error) {
    throw error;
  }
}


async function main() {
  const existingUsers =
    await getExistingUsers();

  console.log(
    "SupportPilot staff bootstrap",
  );

  console.log(
    `Supabase: ${supabaseUrl}`,
  );


  for (
    const member
    of staff
  ) {
    const user =
      await ensureAuthUser(
        member,
        existingUsers,
      );

    await ensureProfile(
      member,
      user,
    );

    console.log(
      `READY ${member.role}: ${member.email}`,
    );
  }


  console.log(
    "Staff bootstrap completed successfully.",
  );
}


main().catch(
  (error) => {
    console.error(
      "Staff bootstrap failed:",
      error.message,
    );

    process.exit(1);
  },
);