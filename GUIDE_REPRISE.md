# Guide ultra-simple — reprendre AUTA Gestion

Ce guide est pour quelqu’un qui n’est **pas** à l’aise avec l’ordinateur.  
Lis lentement, une case à la fois. Tu n’as pas besoin de coder.

---

## C’est quoi ?

**AUTA Gestion** = l’appli du garage (dossiers, photos, devis, factures).

Tu as 3 “boîtes” sur internet :

1. **L’appli** (l’écran) → GitHub Pages  
2. **Le cerveau** (l’API) → Render  
3. **Les fichiers** (photos / PDF) → Supabase  

Les factures suivent le modèle **AS AUTOS** (bandeau rouge, infos grises, tableau, totaux).

---

## Liens importants

| Quoi | Lien |
|------|------|
| Ouvrir l’appli | https://reeegency-hub.github.io/auta-gestion/ |
| Compte Render (cerveau) | https://dashboard.render.com |
| Compte Supabase (fichiers) | https://supabase.com/dashboard |
| Compte Brevo (emails) | https://app.brevo.com |
| Compte Grok / xAI (lecture PDF) | https://console.x.ai |

Login actuel (à changer) :  
`Directeur@auta.gestion` / `auta123`

---

## Étape 1 — Se connecter à l’appli (2 min)

1. Ouvre le lien de l’appli (ci-dessus) sur le téléphone ou l’ordi.  
2. Tape l’email + mot de passe.  
3. Si ça met 30–60 secondes la première fois : **attends**, le serveur gratuit se réveille.  
4. Va dans **Paramètres**.  
5. Remplis **ton** garage :
   - Raison sociale (ex. AS AUTOS)
   - Téléphone, email
   - Adresse, SIRET, TVA, RCS
   - Mode de paiement (ex. Chèque)
6. Clique **Enregistrer**.  
7. Change le mot de passe en bas de la page Paramètres.

---

## Étape 2 — Brancher TON Supabase (fichiers) — 10 min

Aujourd’hui les fichiers sont sur un projet Supabase déjà créé.  
Quand tu veux **le tien** :

1. Va sur https://supabase.com → crée un compte (ou connecte-toi).  
2. **New project** → nomme-le (ex. `as-autos`) → Europe.  
3. Attends que le projet soit prêt (barre verte).  
4. Menu gauche → **Project Settings** (engrenage) → **API**.  
5. Copie :
   - **Project URL** (commence par `https://…supabase.co`)
   - **service_role** (secret) — clique pour révéler, copie tout  
     ⚠️ pas la clé `anon`
6. Va sur https://dashboard.render.com  
7. Clique le service **auta-gestion-api**  
8. Menu **Environment**  
9. Modifie (ou ajoute) :
   - `SUPABASE_URL` = ton Project URL  
   - `SUPABASE_SERVICE_ROLE_KEY` = ta service_role  
   - `SUPABASE_BUCKET` = `auta`  
10. **Save** → Render redémarre tout seul (2–3 min).  
11. Dans Supabase → **Storage** → crée un bucket nommé `auta` (privé) si besoin.  
    (L’appli essaie aussi de le créer toute seule.)

Test : dans l’appli, ajoute une photo sur un dossier. Si elle s’affiche → OK.

---

## Étape 3 — (Plus tard) Base de données Postgres à toi

La base actuelle est sur Render (Postgres free).  
Quand Render demande une carte / upgrade :

1. Render → **New** → **PostgreSQL**  
2. Copie l’**Internal Database URL**  
3. Dans **auta-gestion-api** → Environment → `DATABASE_URL` = cette URL  
4. Save / Redeploy  

⚠️ Changer de base = **nouvelle base vide**. Il faudra recréer le compte et les paramètres.

---

## Étape 4 — Emails (Brevo) — déjà branché

Pour envoyer devis/facture par mail, Brevo est déjà configuré.  
Si tu veux **ton** compte Brevo :

1. https://app.brevo.com → SMTP & API → onglet SMTP  
2. Copie **Login** (`…@smtp-brevo.com`) + **SMTP key**  
3. Sur Render → Environment :
   - `SMTP_HOST` = `smtp-relay.brevo.com`
   - `SMTP_PORT` = `587`
   - `SMTP_USER` = le Login  
   - `SMTP_PASSWORD` = la clé  
   - `SMTP_FROM` = `AS AUTOS <ton-email@…>`  
4. Save.

Désactive la restriction d’IP dans Brevo (sinon ça bloque).

---

## Étape 5 — Lecture auto des PDF (Grok) — optionnel

Sans crédits xAI, tu peux **saisir les lignes à la main** (bouton + Ajouter une opération).

Avec IA :
1. https://console.x.ai → achete des crédits  
2. Crée une clé API  
3. Render → `GROK_API_KEY` = cette clé → Save

---

## Utilisation du quotidien (ordre simple)

1. Créer un **dossier** (client + voiture)  
2. Ajouter des **photos**  
3. Importer le **PDF d’expertise** (ou saisir les lignes)  
4. **Valider** l’expertise  
5. Créer le **devis** → vérifier → valider  
6. Créer la **facture** (même look AS AUTOS)  
7. **Envoyer** par email si besoin  
8. Marquer **payée** / **livrée**

---

## Si ça marche pas

| Problème | Que faire |
|----------|-----------|
| Login long / erreur | Attendre 1 min, réessayer (serveur endormi) |
| Photo invisible | Vérifier Supabase URL + service_role sur Render |
| Email échoue | Vérifier SMTP Brevo + IP autorisées |
| PDF expertise vide | Saisir les lignes à la main ou ajouter crédits Grok |
| “Inscription fermée” | Normal : seul l’admin crée les comptes |

---

## Ce qu’il ne faut PAS faire

- Ne partage pas la clé `service_role` Supabase (c’est le passe-partout).  
- Ne remets pas `ALLOW_OPEN_REGISTRATION=true` en public.  
- Ne supprime pas le service Render sans avoir noté les variables.  
- Avant fin **août**, upgrade le Postgres Render free (sinon risque de perte).

---

## Qui a créé quoi ?

Tout a été préparé pour toi. Toi, tu dois surtout :

1. Remplir **Paramètres** avec AS AUTOS  
2. Changer le **mot de passe**  
3. Plus tard : coller **ton** Supabase (et éventuellement Postgres / Brevo / Grok)

Si tu es perdu : demande à la personne qui t’a mis ça en place, avec une **capture d’écran** de l’erreur.
