# Minisforum X1 Pro-470: Windows Backup & Linux/ROCm Migration Runbook

Follow this in order. Do not skip ahead to Phase 2 until every checkbox in
Phase 1 is genuinely done -- that's the whole point of this runbook.

---

## Phase 1: Verify, Back Up, Prepare Recovery Media

**Goal: make the wipe in Phase 2 fully reversible before it happens.**

### What each piece of recovery media actually is (read this first)

Easy to mix these up, so here's the plain version:

- **Disk image** = a photograph of your *actual, current* Windows machine --
  every file, every setting, every program, exactly as it is today. This is
  the real safety net. If Linux doesn't work out, restoring this gets you
  back to *your* machine, not a blank one.
- **Windows 11 ISO file** = a blank, generic installer -- no personalization,
  the same file anyone downloads from Microsoft. Not a backup of anything
  on this machine. It only exists as a backup-of-the-backup: if the Rufus
  USB itself ever gets lost or corrupted, this saved copy lets you rebuild
  a new bootable USB without re-downloading several GB from Microsoft.
- **Rufus USB** = the physical, bootable tool built *from* that ISO file --
  the thing you'd actually plug in and boot from.
- **License key** = only matters if you ever install Windows completely
  fresh instead of restoring the disk image.

**The real rollback sequence, if you ever need it:** boot the Rufus USB >
click "Repair your computer" (not "Install now") > System Image Recovery >
point it at the disk image on the T7 > it restores everything > reboot into
Windows exactly as it was.

### 1.1 Power on and verify Windows

- [ ] Boot the Minisforum. Confirm it boots straight into Windows 11 Pro
      normally -- desktop loads, no errors, no unexpected first-run setup
      screens (which would suggest this is somehow not the state you expect).
- [ ] Confirm network connectivity (Wi-Fi or Ethernet) so Windows Update and
      license activation checks can reach Microsoft if needed.

### 1.2 Retrieve and record the license key

Open PowerShell **as Administrator** (right-click Start > Terminal (Admin)):

```powershell
Get-CimInstance -ClassName SoftwareLicensingService | Select OA3xOriginalProductKey
```

- [ ] If it returns a 25-character key (format `XXXXX-XXXXX-XXXXX-XXXXX-XXXXX`),
      **write it down somewhere durable** -- a physical note, a password
      manager, or a text file saved to the T7 in step 1.4. This confirms the
      OEM key is embedded in firmware and travels with the hardware.
- [ ] If it returns blank: confirm you're signed into Windows with the
      Microsoft account tied to this machine's digital entitlement instead.
      Note that down as the fallback activation method.

### 1.3 Full disk image backup to the T7

- [ ] Plug in the Samsung T7. Confirm Windows recognizes it and note its
      drive letter (e.g. `E:`).
- [ ] Search Start menu for **"Create a system image"** (or Control Panel >
      Backup and Restore (Windows 7) > Create a system image).
- [ ] Select **"On a hard disk"** and choose the T7 as the destination.
- [ ] Confirm it's including the system drive (should be selected by
      default).
- [ ] Start the backup. This can take 30-90+ minutes depending on how much
      is actually used on the drive -- let it run to completion, don't
      interrupt it.
- [ ] When it finishes, it will ask if you want to create a system repair
      disc -- you can skip this since you already have a Windows 11 USB
      installer (from earlier this week), but note that repair discs and
      installer USBs serve slightly different recovery purposes.
- [ ] **Verify the image exists**: browse to the T7 in File Explorer,
      confirm a `WindowsImageBackup` folder is present with real content
      inside it (several GB at minimum).

### 1.4 Save the license key and download a Windows 11 ISO copy to the T7

- [ ] Create a plain text file on the T7 (e.g. `T7:\minisforum-recovery\license-key.txt`)
      with the OEM key from step 1.2, the date, and a note like "Minisforum
      X1 Pro-470 OEM key, confirmed via firmware."
- [ ] Download the Windows 11 ISO directly from Microsoft
      (search "download windows 11 disk image", use the official
      microsoft.com page, not a third-party mirror).
- [ ] Save that `.iso` file itself onto the T7, in the same recovery folder.
      This is a second, independent copy separate from the bootable Rufus
      USB you already made -- if the USB drive is ever lost, corrupted, or
      overwritten, you still have the raw ISO to build a new one from.

### 1.5 Confirm the Rufus recovery USB is real and bootable

- [ ] Confirm the drive still has the Windows 11 installer on it (browse it
      in File Explorer -- should show `setup.exe`, a `sources` folder, etc.,
      not be empty).
- [ ] Set it aside physically with the T7 as your "if this goes wrong" kit.

### Phase 1 checkpoint -- do not proceed until all of these are true:

- [ ] License key (or Microsoft account fallback) written down in at least
      two places
- [ ] Full disk image verified present on the T7
- [ ] Windows 11 ISO file copy saved on the T7
- [ ] Rufus USB confirmed bootable/populated

---

## Phase 2: Wipe and Install Ubuntu Server

**Goal: a clean Ubuntu 24.04 LTS install, confirmed booting, before touching
ROCm or Docker.**

### 2.1 Download Ubuntu Server 24.04 LTS

- [ ] From ubuntu.com, download the **Ubuntu Server** (not Desktop) 24.04
      LTS ISO. Server avoids unnecessary GUI overhead on a headless 24/7
      compute node.

### 2.2 Build a second bootable USB for Ubuntu

- [ ] Use a **separate** USB stick from the Windows recovery one --
      reusing that drive would overwrite your Windows recovery media.
- [ ] Open Rufus, select the new stick, point it at the Ubuntu Server ISO,
      GPT partition scheme, UEFI target, same as the Windows one. Run it.

### 2.3 Boot from the Ubuntu installer and install

- [ ] Insert the Ubuntu USB into the Minisforum, power on, enter the boot
      menu (usually F7, F11, or Del/Esc depending on firmware -- watch the
      boot splash for the prompt), select the USB drive.
- [ ] Follow the Ubuntu Server installer: language, keyboard, network
      (set a static IP or note the DHCP-assigned one -- you'll want this
      consistent for the control plane's IP addressing), and when asked
      about the disk, **select the full-disk wipe/erase option** -- this is
      the actual point of no return, confirmed safe because Phase 1 is done.
- [ ] When prompted, enable **OpenSSH server** during install if offered --
      makes remote administration much easier than working at the box
      directly going forward.
- [ ] Complete the install, reboot when prompted, remove the USB when told to.

### Phase 2 checkpoint:

- [ ] Ubuntu boots to a login prompt
- [ ] `lsb_release -a` shows Ubuntu 24.04 LTS
- [ ] You can log in with the user account created during setup

---

## Phase 3: ROCm and Docker Setup

**Goal: the RX 9070 XT recognized by ROCm, Docker Engine installed, GPU
passthrough permissions correct.**

### 3.1 Update the system first

```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### 3.2 Install ROCm (compute use case, not full desktop graphics)

```bash
sudo apt install -y "linux-headers-$(uname -r)" "linux-modules-extra-$(uname -r)"
wget https://repo.radeon.com/amdgpu-install/latest/ubuntu/noble/amdgpu-install_6.x.x-1_all.deb
sudo apt install -y ./amdgpu-install_6.x.x-1_all.deb
sudo apt update
sudo amdgpu-install --usecase=rocm,hiplibsdk -y
sudo reboot
```

(Check repo.radeon.com for the current exact `.deb` filename/version at
install time -- these version numbers shift.)

### 3.3 Add your user to the required groups

```bash
sudo usermod -a -G render,video $USER
```

- [ ] **Log out and back in** (or reboot) -- group membership doesn't take
      effect in your current session otherwise.
- [ ] Verify: `id $USER` should list both `render` and `video`.

### 3.4 Confirm ROCm sees the GPU

```bash
rocminfo
```

- [ ] Look for `Name: gfx1201` in the output. If it's not there, or the
      command errors, stop here -- don't proceed to Docker until this
      genuinely works, since Docker passthrough can't fix a driver problem
      underneath it.

### 3.5 Install Docker Engine (native, not Docker Desktop)

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -a -G docker $USER
```

- [ ] Log out and back in again for the docker group to apply.
- [ ] Verify: `docker --version` and `docker compose version` both return
      real version numbers.

### Phase 3 checkpoint:

- [ ] `rocminfo` shows `gfx1201`
- [ ] `id $USER` shows `render`, `video`, and `docker` groups
- [ ] `docker --version` works without needing `sudo`

---

## Phase 4: Deploy the Control Plane

### 4.1 Get the repo

```bash
git clone https://github.com/rodnice007-lang/adversarial-ai-control-plane.git
cd adversarial-ai-control-plane
```

- [ ] Confirm `docker-compose.minisforum.yml`, `main.py`, `requirements.txt`,
      and `Dockerfile` are all present at the root.

### 4.2 Create real secrets

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Create `.env` at the repo root:

```
REDIS_PASSWORD=<first generated value>
ADMIN_API_KEY=<second generated value>
```

- [ ] Confirm `.gitignore` already excludes `.env` (it should, from the repo).

### 4.3 Bring the stack up

```bash
docker compose -f docker-compose.minisforum.yml up --build
```

- [ ] Watch the `ollama` service build/start specifically -- no ROCm-related
      errors during pull or startup.
- [ ] Confirm you see `Uvicorn running on http://0.0.0.0:8443` in the
      `control-plane` logs, same success signal as the laptop deployment.

### 4.4 Verify GPU is actually in use, then test end-to-end

In a second terminal:

```bash
docker exec ollama rocminfo | grep gfx1201
curl http://localhost:8443/healthz
```

- [ ] `healthz` returns `{"status":"ok"}`.

Then pull the model (temporarily connect Ollama to `edge` for internet
access, same procedure as the laptop):

```bash
docker network connect adversarial-ai-control-plane_edge ollama
docker exec ollama ollama pull qwen2.5:3b
docker network disconnect adversarial-ai-control-plane_edge ollama
```

Then the real test:

```bash
curl -X POST http://localhost:8443/api/chat \
  -H "X-API-Key: <your ADMIN_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"hello"}]}'
```

- [ ] A real model response comes back -- confirms RBAC, the identity
      policy check, LLM Guard scanning, and ROCm-accelerated inference all
      worked together, on the new hardware, for the first time.

### Phase 4 checkpoint -- migration complete when:

- [ ] All three containers running (`docker ps` shows control-plane,
      ollama, redis)
- [ ] GPU confirmed in use, not silent CPU fallback
- [ ] End-to-end chat request succeeds with a real response
- [ ] `docker network ls` shows Ollama disconnected from `edge` again after
      the pull (isolation restored)



