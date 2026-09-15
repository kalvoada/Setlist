# Setlist

A social app for sharing music. Every post is a song, album or playlist from a
streaming service.

```
Setlist/
├── app-ios/     SwiftUI client (MVVM)
└── backend/     FastAPI + SQLAlchemy REST API
```

## Features

| Area | What works |
| --- | --- |
| Accounts | Register, sign in with username or e-mail, JWT sessions kept in the Keychain, token refresh on launch |
| Posts | Paste a Spotify / Apple Music / YouTube Music / SoundCloud / TIDAL / Deezer / Bandcamp link, see the resolved track, add a caption. A post without music is rejected |
| Feed | "Following" timeline plus a global "Discover" timeline, paged and pull-to-refresh |
| Follows | Follow and unfollow, follower/following lists and counts, follow suggestions |
| Likes | Like and unlike with optimistic UI, like counts, who-liked lists, and a "posts you liked" screen |
| Comments | Threaded under each post; deletable by the comment's author or the post's owner |
| Profile settings | Display name, bio and avatar |
| Account settings | Change username, e-mail or password (each confirmed with the current password) and delete the account with everything attached to it |

### Configuration

Everything is read from the environment (see `.env.example`):

| Variable | Default | Notes |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./social.db` | Use Postgres in production: `postgresql+psycopg://…` |
| `SECRET_KEY` | dev-only value | **Required in production**: 32+ random characters. The app refuses to start without it |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` (7 days) | |
| `CORS_ORIGINS` | `*` | Comma-separated list |
| `ENABLE_LINK_METADATA` | `true` | Looks up title/artwork through the providers' public oEmbed endpoints |
| `ENVIRONMENT` | `development` | `production` enables the checks above and disables auto-created tables |


### API

All list endpoints return `{ items, limit, offset, total, has_more }` and take
`?limit=&offset=`. Authenticated endpoints expect `Authorization: Bearer <token>`.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/auth/register` | Create an account, returns a token and the user |
| `POST` | `/auth/login` | Sign in with username **or** e-mail |
| `POST` | `/auth/refresh` | Exchange a valid token for a fresh one |
| `GET` | `/users/me` | The signed-in user |
| `PATCH` | `/users/me` | Edit display name, bio, avatar |
| `PATCH` | `/users/me/account` | Change username / e-mail / password |
| `DELETE` | `/users/me` | Delete the account |
| `GET` | `/users/search?q=` | Search by username or display name |
| `GET` | `/users/suggested` | People to follow |
| `GET` | `/users/{id}` | A profile with counters and follow state |
| `GET` | `/users/{id}/posts` | That person's posts |
| `POST`/`DELETE` | `/users/{id}/follow` | Follow / unfollow |
| `GET` | `/users/{id}/followers`, `/following` | The follow graph |
| `POST` | `/posts/resolve-link` | Turn a streaming link into a preview |
| `POST` | `/posts/` | Create a post (a valid music link is required) |
| `GET` | `/posts/` | Discover timeline |
| `GET` | `/posts/feed` | Posts from the people you follow, plus your own |
| `GET` | `/posts/liked` | Posts you liked |
| `GET`/`PATCH`/`DELETE` | `/posts/{id}` | Read, edit the caption, delete |
| `POST`/`DELETE` | `/posts/{id}/like` | Like / unlike |
| `GET` | `/posts/{id}/likes` | Who liked it |
| `GET`/`POST` | `/posts/{id}/comments` | Read and add comments |
| `DELETE` | `/comments/{id}` | Delete a comment |

## iOS app

```
app-ios/Setlist/
├── App/            entry point and theme
├── Models/         Codable models mirroring the API
├── Networking/     APIService, APIError, Keychain storage
├── ViewModels/     one @Observable model per screen
├── Views/          screens, plus reusable Components/
└── SetlistTests/   decoding, request shape, error mapping, view-model tests
```
